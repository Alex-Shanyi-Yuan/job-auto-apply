from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import json
import logging
from pathlib import Path
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from database import create_db_and_tables, get_session, Job, engine
from core import JobParsingAgent, ResumeTailorAgent, compile_pdf

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Allow Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
SCRAPER_SERVICE_URL = os.getenv("SCRAPER_SERVICE_URL", "http://scraper:8001")
MASTER_RESUME_PATH = os.getenv("MASTER_RESUME_PATH", "./data/master.tex")

class ApplyRequest(BaseModel):
    url: str

class JobResponse(BaseModel):
    id: int
    url: str
    company: str
    title: str
    status: str
    requirements: Optional[List[str]] = None
    created_at: str

def load_master_resume(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Master resume not found: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

async def process_application(job_id: int, url: str):
    logger.info(f"Starting processing for job {job_id} with URL: {url}")
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found in database")
            return

        try:
            # 1. Scrape
            logger.debug(f"Scraping URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(f"{SCRAPER_SERVICE_URL}/scrape", json={"url": url}, timeout=60.0)
                response.raise_for_status()
                data = response.json()
                raw_text = data["text"]
            logger.debug("Scraping completed successfully")
            
            # 2. Parse
            logger.debug("Parsing job description")
            parsing_agent = JobParsingAgent()
            job_posting = parsing_agent.parse(raw_text)
            
            # Update job details
            job.company = job_posting.company_name
            job.title = job_posting.job_title
            if job_posting.key_requirements:
                job.requirements = json.dumps(job_posting.key_requirements)
            session.add(job)
            session.commit()
            logger.info(f"Job parsed: {job.company} - {job.title}")
            
            # 3. Tailor
            logger.debug("Tailoring resume")
            master_latex = load_master_resume(MASTER_RESUME_PATH)
            tailor_agent = ResumeTailorAgent()
            tailored_latex = tailor_agent.tailor(master_latex, job_posting)
            
            # 4. Compile
            logger.debug("Compiling PDF")
            # Sanitize company name for filename
            company_name = "".join(c for c in job_posting.company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            
            pdf_path = compile_pdf(
                latex_content=tailored_latex,
                output_dir="./output",
                company_name=company_name,
                cleanup=True
            )
            
            # 5. Save path
            job.pdf_path = pdf_path
            job.status = "applied"
            session.add(job)
            session.commit()
            logger.info(f"Job {job_id} processing completed successfully. PDF saved at {pdf_path}")
            
        except Exception as e:
            logger.exception(f"Error processing job {job_id}: {e}")
            job.status = "failed"
            session.add(job)
            session.commit()

@app.post("/apply", response_model=JobResponse)
async def apply_job(request: ApplyRequest, background_tasks: BackgroundTasks):
    # Create initial job record
    job = Job(url=request.url, company="Pending...", title="Pending...", status="processing")
    
    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)
    
    # Start background processing
    background_tasks.add_task(process_application, job.id, request.url)
    
    return JobResponse(
        id=job.id,
        url=job.url,
        company=job.company,
        title=job.title,
        status=job.status,
        requirements=json.loads(job.requirements) if job.requirements else None,
        created_at=job.created_at.isoformat()
    )

@app.get("/jobs", response_model=List[JobResponse])
def list_jobs():
    with Session(engine) as session:
        jobs = session.exec(select(Job).order_by(Job.created_at.desc())).all()
        return [
            JobResponse(
                id=job.id,
                url=job.url,
                company=job.company,
                title=job.title,
                status=job.status,
                requirements=json.loads(job.requirements) if job.requirements else None,
                created_at=job.created_at.isoformat()
            ) for job in jobs
        ]

@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return JobResponse(
            id=job.id,
            url=job.url,
            company=job.company,
            title=job.title,
            status=job.status,
            requirements=json.loads(job.requirements) if job.requirements else None,
            created_at=job.created_at.isoformat()
        )

@app.get("/jobs/{job_id}/pdf")
def get_job_pdf(job_id: int):
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.pdf_path or not os.path.exists(job.pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
            
        return FileResponse(job.pdf_path, media_type="application/pdf", filename=os.path.basename(job.pdf_path))
