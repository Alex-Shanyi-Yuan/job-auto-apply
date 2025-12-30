from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import httpx
import os
import json
import logging
import asyncio
from pathlib import Path
from datetime import datetime
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from database import create_db_and_tables, get_session, Job, JobSource, engine
from core import JobParsingAgent, ResumeTailorAgent, JobDiscoveryAgent, JobScoringAgent, compile_pdf

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
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "3.0"))  # Seconds between scrapes

# Global scan status tracking
scan_status = {
    "is_scanning": False,
    "current_source": None,
    "current_source_id": None,
    "sources_total": 0,
    "sources_completed": 0,
    "jobs_found": 0,
    "jobs_scored": 0,
    "current_step": None,  # "scraping", "discovering", "scoring"
    "error": None,
}


# === Request/Response Models ===

class ApplyRequest(BaseModel):
    url: str


class JobResponse(BaseModel):
    id: int
    url: str
    company: str
    title: str
    status: str
    score: Optional[int] = None
    requirements: Optional[List[str]] = None
    created_at: str


class JobSourceCreate(BaseModel):
    url: str
    name: str
    filter_prompt: str


class JobSourceResponse(BaseModel):
    id: int
    url: str
    name: str
    filter_prompt: str
    last_scraped_at: Optional[str] = None
    created_at: str


class RefreshResponse(BaseModel):
    message: str
    sources_count: int


class ScanStatusResponse(BaseModel):
    is_scanning: bool
    current_source: Optional[str] = None
    current_source_id: Optional[int] = None
    sources_total: int
    sources_completed: int
    jobs_found: int
    jobs_scored: int
    current_step: Optional[str] = None
    error: Optional[str] = None


# === Helper Functions ===

def load_master_resume(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Master resume not found: {file_path}")
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def job_to_response(job: Job) -> JobResponse:
    return JobResponse(
        id=job.id,
        url=job.url,
        company=job.company,
        title=job.title,
        status=job.status,
        score=job.score,
        requirements=json.loads(job.requirements) if job.requirements else None,
        created_at=job.created_at.isoformat()
    )


def source_to_response(source: JobSource) -> JobSourceResponse:
    return JobSourceResponse(
        id=source.id,
        url=source.url,
        name=source.name,
        filter_prompt=source.filter_prompt,
        last_scraped_at=source.last_scraped_at.isoformat() if source.last_scraped_at else None,
        created_at=source.created_at.isoformat()
    )

# === Background Tasks ===

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


async def process_job_discovery():
    """Background task to discover and score jobs from all sources."""
    global scan_status
    logger.info("Starting job discovery process...")
    
    # Reset scan status
    scan_status = {
        "is_scanning": True,
        "current_source": None,
        "current_source_id": None,
        "sources_total": 0,
        "sources_completed": 0,
        "jobs_found": 0,
        "jobs_scored": 0,
        "current_step": "initializing",
        "error": None,
    }
    
    try:
        with Session(engine) as session:
            sources = session.exec(select(JobSource)).all()
            
            if not sources:
                logger.info("No job sources configured")
                scan_status["is_scanning"] = False
                scan_status["current_step"] = "completed"
                return
            
            scan_status["sources_total"] = len(sources)
            
            # Load master resume once for scoring
            try:
                master_resume = load_master_resume(MASTER_RESUME_PATH)
            except FileNotFoundError:
                logger.error("Master resume not found, skipping scoring")
                master_resume = None
            
            discovery_agent = JobDiscoveryAgent()
            scoring_agent = JobScoringAgent() if master_resume else None
            
            for source in sources:
                scan_status["current_source"] = source.name
                scan_status["current_source_id"] = source.id
                scan_status["current_step"] = "scraping"
                logger.info(f"Processing source: {source.name} ({source.url})")
                
                try:
                    # 1. Scrape the search results page (HTML format)
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"{SCRAPER_SERVICE_URL}/scrape",
                            json={"url": source.url, "format": "html"},
                            timeout=60.0
                        )
                        response.raise_for_status()
                        data = response.json()
                        html_content = data["text"]
                    
                    # 2. Discover jobs using AI
                    scan_status["current_step"] = "discovering"
                    discovered_jobs = discovery_agent.discover(html_content, source.filter_prompt)
                    logger.info(f"Discovered {len(discovered_jobs)} jobs from {source.name}")
                    scan_status["jobs_found"] += len(discovered_jobs)
                    
                    # 3. Process each discovered job
                    new_jobs_count = 0
                    for dj in discovered_jobs:
                        # Check if job already exists (by URL)
                        existing = session.exec(select(Job).where(Job.url == dj.url)).first()
                        if existing:
                            logger.debug(f"Job already exists: {dj.url}")
                            continue
                        
                        # Rate limiting - wait before scraping job details
                        await asyncio.sleep(RATE_LIMIT_DELAY)
                        
                        # Scrape individual job page for scoring
                        score = None
                        if scoring_agent:
                            scan_status["current_step"] = f"scoring: {dj.title[:30]}..."
                            try:
                                async with httpx.AsyncClient() as client:
                                    job_response = await client.post(
                                        f"{SCRAPER_SERVICE_URL}/scrape",
                                        json={"url": dj.url, "format": "text"},
                                        timeout=60.0
                                    )
                                    job_response.raise_for_status()
                                    job_text = job_response.json()["text"]
                                    
                                # Score the job
                                job_score = scoring_agent.score(job_text, master_resume)
                                score = job_score.score
                                scan_status["jobs_scored"] += 1
                                logger.info(f"Scored job '{dj.title}': {score}/100 - {job_score.reasoning}")
                            except Exception as e:
                                logger.warning(f"Failed to score job {dj.url}: {e}")
                        
                        # Save new job
                        new_job = Job(
                            url=dj.url,
                            company=dj.company,
                            title=dj.title,
                            status="suggested",
                            score=score,
                            source_id=source.id
                        )
                        session.add(new_job)
                        new_jobs_count += 1
                    
                    # Update source last_scraped_at
                    source.last_scraped_at = datetime.utcnow()
                    session.add(source)
                    session.commit()
                    
                    scan_status["sources_completed"] += 1
                    logger.info(f"Added {new_jobs_count} new jobs from {source.name}")
                    
                except Exception as e:
                    logger.exception(f"Error processing source {source.name}: {e}")
                    scan_status["error"] = f"Error processing {source.name}: {str(e)}"
                    continue
        
        logger.info("Job discovery process completed")
    
    finally:
        scan_status["is_scanning"] = False
        scan_status["current_step"] = "completed"
        scan_status["current_source"] = None

@app.post("/apply", response_model=JobResponse)
async def apply_job(request: ApplyRequest, background_tasks: BackgroundTasks):
    """Start the application process for a job URL."""
    # Create initial job record
    job = Job(url=request.url, company="Pending...", title="Pending...", status="processing")
    
    with Session(engine) as session:
        session.add(job)
        session.commit()
        session.refresh(job)
    
    # Start background processing
    background_tasks.add_task(process_application, job.id, request.url)
    
    return job_to_response(job)


@app.get("/jobs", response_model=List[JobResponse])
def list_jobs():
    """List all jobs (excluding suggested/dismissed)."""
    with Session(engine) as session:
        jobs = session.exec(
            select(Job)
            .where(Job.status.not_in(["suggested", "dismissed"]))
            .order_by(Job.created_at.desc())
        ).all()
        return [job_to_response(job) for job in jobs]


@app.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: int):
    """Get a specific job by ID."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job_to_response(job)


@app.get("/jobs/{job_id}/pdf")
def get_job_pdf(job_id: int):
    """Download the tailored resume PDF for a job."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if not job.pdf_path or not os.path.exists(job.pdf_path):
            raise HTTPException(status_code=404, detail="PDF not found")
            
        return FileResponse(job.pdf_path, media_type="application/pdf", filename=os.path.basename(job.pdf_path))


# === Job Sources API ===

@app.post("/sources", response_model=JobSourceResponse)
def create_source(source: JobSourceCreate):
    """Create a new job source to scan."""
    with Session(engine) as session:
        db_source = JobSource(
            url=source.url,
            name=source.name,
            filter_prompt=source.filter_prompt
        )
        session.add(db_source)
        session.commit()
        session.refresh(db_source)
        return source_to_response(db_source)


@app.get("/sources", response_model=List[JobSourceResponse])
def list_sources():
    """List all configured job sources."""
    with Session(engine) as session:
        sources = session.exec(select(JobSource).order_by(JobSource.created_at.desc())).all()
        return [source_to_response(s) for s in sources]


@app.delete("/sources/{source_id}")
def delete_source(source_id: int):
    """Delete a job source."""
    with Session(engine) as session:
        source = session.get(JobSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        session.delete(source)
        session.commit()
        return {"ok": True}


# === Suggestions API ===

@app.get("/suggestions", response_model=List[JobResponse])
def list_suggestions():
    """List all suggested jobs, ordered by score."""
    with Session(engine) as session:
        jobs = session.exec(
            select(Job)
            .where(Job.status == "suggested")
            .order_by(Job.score.desc(), Job.created_at.desc())
        ).all()
        return [job_to_response(job) for job in jobs]


@app.post("/suggestions/refresh", response_model=RefreshResponse)
async def refresh_suggestions(background_tasks: BackgroundTasks):
    """Trigger job discovery from all configured sources."""
    with Session(engine) as session:
        sources_count = len(session.exec(select(JobSource)).all())
    
    if sources_count == 0:
        raise HTTPException(status_code=400, detail="No job sources configured. Add a source first.")
    
    background_tasks.add_task(process_job_discovery)
    
    return RefreshResponse(
        message="Job discovery started in background",
        sources_count=sources_count
    )


@app.post("/jobs/{job_id}/dismiss", response_model=JobResponse)
def dismiss_job(job_id: int):
    """Dismiss a suggested job (hide it from suggestions)."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.status = "dismissed"
        session.add(job)
        session.commit()
        session.refresh(job)
        return job_to_response(job)


@app.get("/suggestions/status", response_model=ScanStatusResponse)
def get_scan_status():
    """Get the current status of the job discovery scan."""
    return ScanStatusResponse(**scan_status)
