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
from urllib.parse import urljoin, urlparse
from sqlmodel import Session, select
from contextlib import asynccontextmanager

from database import create_db_and_tables, get_session, Job, JobSource, Settings, engine
from core import JobParsingAgent, ResumeTailorAgent, JobDiscoveryAgent, JobScoringAgent, compile_pdf

# Configure Logging
logging.basicConfig(
    level=logging.DEBUG if os.getenv("DEBUG", "false").lower() == "true" else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# only google needs this right now
def resolve_job_url(job_url: str, source_url: str) -> str:
    """
    Resolve a job URL that may be relative to an absolute URL.
    
    Args:
        job_url: The job URL (may be relative like '/jobs/123' or 'jobs/123')
        source_url: The source page URL to use as base for resolution
    
    Returns:
        Absolute URL to the job posting
    """
    # If already absolute, return as-is
    if job_url.startswith('http://') or job_url.startswith('https://'):
        return job_url
    
    # Parse the source URL to get the base
    parsed = urlparse(source_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    
    # If job_url starts with '/', it's root-relative
    if job_url.startswith('/'):
        return base_url + job_url
    
    # Otherwise, use urljoin with the base URL (not the full path)
    # This handles relative paths like 'jobs/results/123'
    return urljoin(base_url + '/', job_url)

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
RATE_LIMIT_DELAY = float(os.getenv("RATE_LIMIT_DELAY", "0.2"))  # Seconds between scrapes (reduced for speed)
MAX_CONCURRENT_SOURCES = int(os.getenv("MAX_CONCURRENT_SOURCES", "5"))  # Max parallel source scans
MAX_CONCURRENT_JOBS = int(os.getenv("MAX_CONCURRENT_JOBS", "10"))  # Max parallel job scrapes per source

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
    "source_results": [],  # Per-source scan results for report
    "active_sources": [],  # List of currently scanning source names (for parallel)
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
    error_message: Optional[str] = None
    created_at: str


class JobSourceCreate(BaseModel):
    url: str
    name: str
    filter_prompt: Optional[str] = None


class JobSourceUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    filter_prompt: Optional[str] = None


class JobSourceResponse(BaseModel):
    id: int
    url: str
    name: str
    filter_prompt: Optional[str] = None
    last_scraped_at: Optional[str] = None
    created_at: str


class RefreshRequest(BaseModel):
    source_ids: Optional[List[int]] = None  # If None, scan all sources


class RefreshResponse(BaseModel):
    message: str
    sources_count: int


class JobInfo(BaseModel):
    id: Optional[int] = None
    title: str
    company: str
    url: str
    score: Optional[int] = None
    skip_reason: Optional[str] = None  # 'already_exists', 'low_score', 'scrape_failed'


class SourceScanResult(BaseModel):
    source_id: int
    source_name: str
    source_url: str
    jobs_found: int
    jobs_added: int
    jobs_skipped: int  # Already existed in DB
    added_jobs: List[JobInfo] = []  # Details of newly added jobs
    skipped_jobs: List[JobInfo] = []  # Details of jobs that already existed
    error: Optional[str] = None


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
    source_results: List[SourceScanResult] = []
    active_sources: List[str] = []  # Currently scanning sources (for parallel)


class GlobalFilterResponse(BaseModel):
    filter_prompt: str


class GlobalFilterUpdate(BaseModel):
    filter_prompt: str


# === Helper Functions ===

GLOBAL_FILTER_KEY = "global_filter_prompt"


def get_global_filter() -> str:
    """Get the global filter prompt from settings."""
    with Session(engine) as session:
        setting = session.get(Settings, GLOBAL_FILTER_KEY)
        return setting.value if setting else ""


def set_global_filter(value: str) -> None:
    """Set the global filter prompt in settings."""
    with Session(engine) as session:
        setting = session.get(Settings, GLOBAL_FILTER_KEY)
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
        else:
            setting = Settings(key=GLOBAL_FILTER_KEY, value=value)
        session.add(setting)
        session.commit()


def get_combined_filter(source: JobSource) -> str:
    """Combine global filter with source-specific filter."""
    global_filter = get_global_filter()
    source_filter = source.filter_prompt or ""
    
    if global_filter and source_filter:
        return f"{global_filter}. Additionally: {source_filter}"
    return global_filter or source_filter or "Any job posting"


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
        error_message=job.error_message,
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
            job.error_message = str(e)
            session.add(job)
            session.commit()


async def process_single_source(
    source_id: int,
    source_name: str, 
    source_url: str,
    source_filter_prompt: Optional[str],
    discovery_agent: JobDiscoveryAgent,
    scoring_agent: Optional[JobScoringAgent],
    master_resume: Optional[str],
    semaphore: asyncio.Semaphore
) -> dict:
    """Process a single source - scrape, discover, and score jobs.
    
    Returns a source_result dict with job details.
    """
    global scan_status
    
    source_result = {
        "source_id": source_id,
        "source_name": source_name,
        "source_url": source_url,
        "jobs_found": 0,
        "jobs_added": 0,
        "jobs_skipped": 0,
        "added_jobs": [],
        "skipped_jobs": [],
        "error": None,
    }
    
    async with semaphore:
        logger.info(f"Processing source: {source_name} ({source_url})")
        
        # Update active sources
        scan_status["active_sources"].append(source_name)
        scan_status["current_source"] = ", ".join(scan_status["active_sources"])
        
        try:
            # 1. Scrape the search results page (HTML format)
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SCRAPER_SERVICE_URL}/scrape",
                    json={"url": source_url, "format": "html"},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                html_content = data["text"]
            
            # 2. Discover jobs using AI with combined filter
            # Build combined filter
            with Session(engine) as session:
                global_filter_setting = session.exec(
                    select(Settings).where(Settings.key == "global_filter")
                ).first()
                global_filter = global_filter_setting.value if global_filter_setting else ""
            
            if source_filter_prompt and global_filter:
                combined_filter = f"{global_filter}\n\nAdditional filter for this source:\n{source_filter_prompt}"
            elif source_filter_prompt:
                combined_filter = source_filter_prompt
            else:
                combined_filter = global_filter or "Find all software engineering and technical jobs"
            
            # Run LLM call in thread pool to avoid blocking event loop
            discovered_jobs = await asyncio.to_thread(discovery_agent.discover, html_content, combined_filter)
            logger.info(f"Discovered {len(discovered_jobs)} jobs from {source_name}")
            
            # Resolve relative URLs to absolute URLs using source URL as base
            for dj in discovered_jobs:
                dj.url = resolve_job_url(dj.url, source_url)
            
            source_result["jobs_found"] = len(discovered_jobs)
            scan_status["jobs_found"] += len(discovered_jobs)
            
            # 3. Batch check which jobs already exist in DB
            job_urls = [dj.url for dj in discovered_jobs]
            with Session(engine) as session:
                existing_jobs = session.exec(
                    select(Job).where(Job.url.in_(job_urls))
                ).all()
                existing_urls = {job.url: job for job in existing_jobs}
            
            # Separate new jobs from existing ones
            new_jobs_to_process = []
            for dj in discovered_jobs:
                if dj.url in existing_urls:
                    existing = existing_urls[dj.url]
                    logger.debug(f"Job already exists: {dj.url}")
                    source_result["jobs_skipped"] += 1
                    source_result["skipped_jobs"].append({
                        "id": existing.id,
                        "title": existing.title,
                        "company": existing.company,
                        "url": existing.url,
                        "score": existing.score,
                        "skip_reason": "already_exists",
                    })
                else:
                    new_jobs_to_process.append(dj)
            
            logger.info(f"Source '{source_name}': {len(new_jobs_to_process)} new jobs to process, {len(existing_urls)} already exist")
            
            # 4. Process new jobs in parallel with semaphore
            job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)
            
            async def process_single_job(dj):
                """Process a single job - scrape and score."""
                async with job_semaphore:
                    # Small delay for rate limiting
                    await asyncio.sleep(RATE_LIMIT_DELAY)
                    
                    score = None
                    if scoring_agent and master_resume:
                        try:
                            async with httpx.AsyncClient() as client:
                                job_response = await client.post(
                                    f"{SCRAPER_SERVICE_URL}/scrape",
                                    json={"url": dj.url, "format": "text"},
                                    timeout=60.0
                                )
                                job_response.raise_for_status()
                                job_text = job_response.json()["text"]
                                
                            # Score the job in thread pool to avoid blocking event loop
                            job_score = await asyncio.to_thread(scoring_agent.score, job_text, master_resume)
                            score = job_score.score
                            scan_status["jobs_scored"] += 1
                            logger.info(f"Scored job '{dj.title}': {score}/100 - {job_score.reasoning}")
                        except Exception as e:
                            logger.warning(f"Failed to score job {dj.url}: {e}")
                    
                    return {
                        "dj": dj,
                        "score": score
                    }
            
            # Process all new jobs in parallel
            if new_jobs_to_process:
                job_results = await asyncio.gather(
                    *[process_single_job(dj) for dj in new_jobs_to_process],
                    return_exceptions=True
                )
                
                # Save results to database
                for result in job_results:
                    if isinstance(result, Exception):
                        logger.warning(f"Job processing failed: {result}")
                        continue
                    
                    dj = result["dj"]
                    score = result["score"]
                    is_low_score = score is not None and score < 50
                    
                    # Save new job
                    with Session(engine) as session:
                        # Double-check job doesn't exist (race condition protection)
                        existing = session.exec(select(Job).where(Job.url == dj.url)).first()
                        if existing:
                            source_result["jobs_skipped"] += 1
                            source_result["skipped_jobs"].append({
                                "id": existing.id,
                                "title": existing.title,
                                "company": existing.company,
                                "url": existing.url,
                                "score": existing.score,
                                "skip_reason": "already_exists",
                            })
                            continue
                        
                        new_job = Job(
                            url=dj.url,
                            company=dj.company,
                            title=dj.title,
                            status="suggested",
                            score=score,
                            source_id=source_id
                        )
                        session.add(new_job)
                        session.commit()
                        session.refresh(new_job)
                        
                        # Track in report - low score jobs go to skipped, others to added
                        if is_low_score:
                            logger.info(f"Added low-score job '{dj.title}' (score: {score}/100)")
                            source_result["jobs_skipped"] += 1
                            source_result["skipped_jobs"].append({
                                "id": new_job.id,
                                "title": new_job.title,
                                "company": new_job.company,
                                "url": new_job.url,
                                "score": score,
                                "skip_reason": "low_score",
                            })
                        else:
                            source_result["jobs_added"] += 1
                            source_result["added_jobs"].append({
                                "id": new_job.id,
                                "title": new_job.title,
                                "company": new_job.company,
                                "url": new_job.url,
                                "score": score,
                            })
            
            # Update source last_scraped_at
            with Session(engine) as session:
                source = session.exec(select(JobSource).where(JobSource.id == source_id)).first()
                if source:
                    source.last_scraped_at = datetime.utcnow()
                    session.add(source)
                    session.commit()
            
            logger.info(f"Source '{source_name}': found={source_result['jobs_found']}, added={source_result['jobs_added']}, skipped={source_result['jobs_skipped']}")
            
        except Exception as e:
            logger.exception(f"Error processing source {source_name}: {e}")
            source_result["error"] = str(e)
        
        finally:
            # Remove from active sources
            if source_name in scan_status["active_sources"]:
                scan_status["active_sources"].remove(source_name)
            scan_status["current_source"] = ", ".join(scan_status["active_sources"]) if scan_status["active_sources"] else None
            scan_status["sources_completed"] += 1
        
        return source_result


async def process_job_discovery(source_ids: Optional[List[int]] = None):
    """Background task to discover and score jobs from selected sources in parallel.
    
    Args:
        source_ids: Optional list of source IDs to scan. If None, scan all sources.
    """
    global scan_status
    logger.info(f"Starting parallel job discovery process... (source_ids={source_ids})")
    
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
            "source_results": [],
            "active_sources": [],
        }
    
    try:
        # Get sources
        with Session(engine) as session:
            if source_ids:
                sources = session.exec(
                    select(JobSource).where(JobSource.id.in_(source_ids))
                ).all()
            else:
                sources = session.exec(select(JobSource)).all()
            
            if not sources:
                logger.info("No job sources to scan")
                scan_status["is_scanning"] = False
                scan_status["current_step"] = "completed"
                return
            
            # Extract source data before session closes
            source_data = [
                {
                    "id": s.id,
                    "name": s.name,
                    "url": s.url,
                    "filter_prompt": s.filter_prompt
                }
                for s in sources
            ]
        
        scan_status["sources_total"] = len(source_data)
        scan_status["current_step"] = "scanning sources in parallel"
        
        # Load master resume once for scoring
        try:
            master_resume = load_master_resume(MASTER_RESUME_PATH)
        except FileNotFoundError:
            logger.error("Master resume not found, skipping scoring")
            master_resume = None
        
        # Create agents (they are stateless, can be shared)
        discovery_agent = JobDiscoveryAgent()
        scoring_agent = JobScoringAgent() if master_resume else None
        
        # Create semaphore to limit concurrent source processing
        semaphore = asyncio.Semaphore(MAX_CONCURRENT_SOURCES)
        
        # Process all sources in parallel
        tasks = [
            process_single_source(
                source_id=s["id"],
                source_name=s["name"],
                source_url=s["url"],
                source_filter_prompt=s["filter_prompt"],
                discovery_agent=discovery_agent,
                scoring_agent=scoring_agent,
                master_resume=master_resume,
                semaphore=semaphore
            )
            for s in source_data
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Source processing failed with exception: {result}")
                scan_status["source_results"].append({
                    "source_id": 0,
                    "source_name": "Unknown",
                    "source_url": "",
                    "jobs_found": 0,
                    "jobs_added": 0,
                    "jobs_skipped": 0,
                    "added_jobs": [],
                    "skipped_jobs": [],
                    "error": str(result),
                })
            else:
                scan_status["source_results"].append(result)
        
        logger.info("Parallel job discovery process completed")
    
    except Exception as e:
        logger.exception(f"Error in job discovery: {e}")
        scan_status["error"] = str(e)
    
    finally:
        scan_status["is_scanning"] = False
        scan_status["current_step"] = "completed"
        scan_status["current_source"] = None
        scan_status["active_sources"] = []

@app.post("/apply", response_model=JobResponse)
async def apply_job(request: ApplyRequest, background_tasks: BackgroundTasks):
    """Start the application process for a job URL."""
    with Session(engine) as session:
        # Check if job already exists (e.g., from suggestions)
        existing_job = session.exec(
            select(Job).where(Job.url == request.url)
        ).first()
        
        if existing_job:
            # Update existing job to processing status
            existing_job.status = "processing"
            session.add(existing_job)
            session.commit()
            session.refresh(existing_job)
            job = existing_job
        else:
            # Create new job record
            job = Job(url=request.url, company="Pending...", title="Pending...", status="processing")
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

@app.get("/settings/global-filter", response_model=GlobalFilterResponse)
def get_global_filter_endpoint():
    """Get the global filter prompt applied to all sources."""
    return GlobalFilterResponse(filter_prompt=get_global_filter())


@app.put("/settings/global-filter", response_model=GlobalFilterResponse)
def update_global_filter_endpoint(update: GlobalFilterUpdate):
    """Update the global filter prompt applied to all sources."""
    set_global_filter(update.filter_prompt)
    return GlobalFilterResponse(filter_prompt=update.filter_prompt)


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


@app.put("/sources/{source_id}", response_model=JobSourceResponse)
def update_source(source_id: int, updates: JobSourceUpdate):
    """Update a job source."""
    with Session(engine) as session:
        source = session.get(JobSource, source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        
        if updates.url is not None:
            source.url = updates.url
        if updates.name is not None:
            source.name = updates.name
        if updates.filter_prompt is not None:
            source.filter_prompt = updates.filter_prompt
        
        session.add(source)
        session.commit()
        session.refresh(source)
        return source_to_response(source)


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
async def refresh_suggestions(
    background_tasks: BackgroundTasks,
    request: Optional[RefreshRequest] = None
):
    """Trigger job discovery from selected sources.
    
    If source_ids is provided, only scan those sources.
    If source_ids is None or empty, scan all sources.
    """
    with Session(engine) as session:
        if request and request.source_ids:
            # Scan only selected sources
            sources = session.exec(
                select(JobSource).where(JobSource.id.in_(request.source_ids))
            ).all()
            sources_count = len(sources)
            if sources_count == 0:
                raise HTTPException(status_code=400, detail="No valid sources found for the given IDs.")
            source_ids = request.source_ids
        else:
            # Scan all sources
            sources_count = len(session.exec(select(JobSource)).all())
            if sources_count == 0:
                raise HTTPException(status_code=400, detail="No job sources configured. Add a source first.")
            source_ids = None
    
    background_tasks.add_task(process_job_discovery, source_ids)
    
    return RefreshResponse(
        message=f"Job discovery started for {sources_count} source(s)",
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
