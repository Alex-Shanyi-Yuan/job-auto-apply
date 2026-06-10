# AutoCareer Data Flow Documentation

This document details the three primary workflows in AutoCareer with step-by-step explanations and sequence diagrams.

## Table of Contents

1. [Job Discovery Workflow](#1-job-discovery-workflow)
2. [Resume Tailoring Workflow](#2-resume-tailoring-workflow)
3. [Application Tracking Workflow](#3-application-tracking-workflow)

---

## 1. Job Discovery Workflow

The job discovery workflow is AutoCareer's core feature—automatically finding and scoring job opportunities from configured sources.

### Overview

Users configure job board URLs (sources), set a global filter, and click "Refresh Suggestions". The system scans sources in parallel, extracts job listings using AI, resolves URLs, scores each job against the master resume, and saves all jobs (including low scores) with `status=suggested`.

### Sequence Diagram

```
User                Frontend              Resume Tailor            Job Scraper           LLM Engine          PostgreSQL
 │                     │                        │                       │                      │                  │
 │  1. Configure      │                        │                       │                      │                  │
 │     Sources        │                        │                       │                      │                  │
 ├──────────────────> │                        │                       │                      │                  │
 │                    │  POST /sources         │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │                        │  INSERT job_sources   │                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │                       │                      │                  │
 │  2. Set Global     │                        │                       │                      │                  │
 │     Filter         │                        │                       │                      │                  │
 ├──────────────────> │                        │                       │                      │                  │
 │                    │  PUT /settings/        │                       │                      │                  │
 │                    │      global-filter     │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │                        │  UPSERT settings      │                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │                       │                      │                  │
 │  3. Click "Refresh │                        │                       │                      │                  │
 │     Suggestions"   │                        │                       │                      │                  │
 ├──────────────────> │                        │                       │                      │                  │
 │                    │  POST /suggestions/    │                       │                      │                  │
 │                    │       refresh          │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │  {status: started}     │                       │                      │                  │
 │                    │<───────────────────────┤                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  4. Background Task:  │                      │                  │
 │                    │                        │     Spawn parallel    │                      │                  │
 │                    │                        │     source scans      │                      │                  │
 │                    │                        │     (max 5 at once)   │                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  ╔═══════════════════════════════════════╗  │                  │
 │                    │                        │  ║  For Source 1 (parallel thread)       ║  │                  │
 │                    │                        │  ╚═══════════════════════════════════════╝  │                  │
 │                    │                        │  POST /scrape         │                      │                  │
 │                    │                        ├──────────────────────>│                      │                  │
 │                    │                        │                       │  5. Fetch HTML       │                  │
 │                    │                        │                       │     (headless        │                  │
 │                    │                        │                       │      Chrome)         │                  │
 │                    │                        │  {html: "..."}        │                      │                  │
 │                    │                        │<──────────────────────┤                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  6. JobDiscoveryAgent │                      │                  │
 │                    │                        │     extract jobs      │                      │                  │
 │                    │                        ├─────────────────────────────────────────────>│                  │
 │                    │                        │  Prompt: "Extract job listings from HTML,    │                  │
 │                    │                        │           filter by: {global_filter}"        │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  {jobs: [{title, company, url}, ...]}        │                  │
 │                    │                        │<─────────────────────────────────────────────┤                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  7. Resolve relative  │                      │                  │
 │                    │                        │     URLs to absolute  │                      │                  │
 │                    │                        │     (using source     │                      │                  │
 │                    │                        │      base URL)        │                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  ╔═══════════════════════════════════════╗  │                  │
 │                    │                        │  ║  For Job 1 (thread pool, max 10)     ║  │                  │
 │                    │                        │  ╚═══════════════════════════════════════╝  │                  │
 │                    │                        │  8. JobScoringAgent   │                      │                  │
 │                    │                        ├─────────────────────────────────────────────>│                  │
 │                    │                        │  Prompt: "Score job {title} at {company}     │                  │
 │                    │                        │           against resume. Return 0-100."     │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  {score: 87, reasoning: "..."}               │                  │
 │                    │                        │<─────────────────────────────────────────────┤                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  9. Check for         │                      │                  │
 │                    │                        │     duplicates        │                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │  SELECT * WHERE url=?  │                     │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  (existing or null)   │                      │                  │
 │                    │                        │<──────────────────────────────────────────────────────────────┤
 │                    │                        │                       │                      │                  │
 │                    │                        │  10. Save job         │                      │                  │
 │                    │                        │      (if new)         │                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │  INSERT jobs VALUES   │                      │                  │
 │                    │                        │    (url, company, title, score,              │                  │
 │                    │                        │     status='suggested', source_id)           │                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  ║  Repeat steps 8-10 for all jobs          ║                  │
 │                    │                        │  ║  (up to 10 in parallel per source)       ║                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  ║  Repeat steps 4-10 for all sources       ║                  │
 │                    │                        │  ║  (up to 5 sources in parallel)           ║                  │
 │                    │                        │                       │                      │                  │
 │                    │                        │  11. Update source    │                      │                  │
 │                    │                        │      last_scraped_at  │                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │  UPDATE job_sources   │                      │                  │
 │                    │                        │    SET last_scraped_at = NOW()               │                  │
 │                    │                        │                       │                      │                  │
 │  12. Poll Status   │                        │                       │                      │                  │
 │                    │  GET /suggestions/     │                       │                      │                  │
 │                    │      status (every 2s) │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │                        │  Query scan state     │                      │                  │
 │                    │  {is_scanning: true,   │                       │                      │                  │
 │                    │   sources_complete: 3, │                       │                      │                  │
 │                    │   sources_total: 5}    │                       │                      │                  │
 │                    │<───────────────────────┤                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │                    │  ... (poll until       │                       │                      │                  │
 │                    │      is_scanning=false)│                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │  13. Scan Complete │                        │                       │                      │                  │
 │                    │  GET /suggestions/     │                       │                      │                  │
 │                    │      status            │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │  {is_scanning: false,  │                       │                      │                  │
 │                    │   scan_report: {...}}  │                       │                      │                  │
 │                    │<───────────────────────┤                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │  14. Fetch Jobs    │                        │                       │                      │                  │
 │                    │  GET /suggestions      │                       │                      │                  │
 │                    ├───────────────────────>│                       │                      │                  │
 │                    │                        │  SELECT * FROM jobs   │                      │                  │
 │                    │                        │    WHERE status='suggested'                  │                  │
 │                    │                        │    ORDER BY score DESC│                      │                  │
 │                    │                        ├──────────────────────────────────────────────────────────────>│
 │                    │                        │                       │                      │                  │
 │                    │  [{id, title, company, │                       │                      │                  │
 │                    │    score, ...}, ...]   │                       │                      │                  │
 │                    │<───────────────────────┤                       │                      │                  │
 │                    │                        │                       │                      │                  │
 │  15. Display       │                        │                       │                      │                  │
 │      Suggestions   │                        │                       │                      │                  │
 │<────────────────── │                        │                       │                      │                  │
```

### Step-by-Step Explanation

#### Phase 1: Configuration

**Step 1-2: User configures sources and global filter**

- User navigates to `/suggestions` page
- Adds job board URLs via `POST /sources` (e.g., LinkedIn search results, company career pages)
- Sets global filter via `PUT /settings/global-filter` (e.g., "Software Engineer with 5+ years Python experience")
- Both stored in PostgreSQL for persistence

**Key Detail**: Sources must be *search result pages* (lists of jobs), not individual job postings. The AI needs HTML containing multiple job listings to extract.

#### Phase 2: Scan Execution

**Step 3: User initiates scan**

- User clicks "Refresh Suggestions" button
- Frontend sends `POST /suggestions/refresh` with optional source IDs (for targeted scanning)
- Backend returns `{status: "started"}` immediately
- Scan runs as a background task (non-blocking)

**Step 4-7: Source processing (parallel)**

Each source is processed in a separate thread (up to `MAX_CONCURRENT_SOURCES=5`):

1. **Scrape HTML** (Step 5): Backend calls `POST scraper:8001/scrape` with source URL
   - Scraper launches headless Chrome via Playwright
   - Waits for JavaScript to render (configurable timeout)
   - Returns full HTML as string

2. **Extract Jobs** (Step 6): `JobDiscoveryAgent` parses HTML
   - AI receives: HTML content + global filter prompt
   - AI extracts: Array of `{title, company, url}` objects
   - Filter is applied during extraction (AI only returns relevant jobs)

3. **Resolve URLs** (Step 7): Convert relative URLs to absolute
   - Example: `/careers/12345` → `https://example.com/careers/12345`
   - Uses source URL's base domain

**Step 8-10: Job scoring (parallel within each source)**

For each discovered job, score in a thread pool (up to `MAX_CONCURRENT_JOBS=10` per source):

1. **Score Job** (Step 8): `JobScoringAgent` compares job to master resume
   - AI receives: Job title, company, master resume text
   - AI returns: Score 0-100 + reasoning
   - No job description fetched yet (just metadata scoring)

2. **Check Duplicates** (Step 9): Query PostgreSQL for existing URL
   - If job already exists (any status): Skip insertion, track as "already existed" in report
   - Deduplication key: `url` column (UNIQUE constraint)

3. **Save Job** (Step 10): Insert new job with `status=suggested`
   - **All jobs are saved**, including low scores
   - Reasoning: User may want to adjust filter later, re-score without re-scraping

**Step 11: Update source metadata**

- Set `last_scraped_at` timestamp for source
- Used to show "Last scanned: 5 minutes ago" in UI

#### Phase 3: Status Polling

**Step 12-13: Frontend polls for completion**

- Every 2 seconds: `GET /suggestions/status`
- Backend returns:
  ```json
  {
    "is_scanning": true,
    "sources_complete": 3,
    "sources_total": 5,
    "current_source": "LinkedIn Python Jobs"
  }
  ```
- UI shows progress bar: "Scanning 3/5 sources..."
- When `is_scanning=false`, poll stops

**Step 14-15: Display results**

- Frontend fetches `GET /suggestions` (jobs with `status=suggested`, sorted by score DESC)
- Renders list with color-coded score badges:
  - Green (80-100): Excellent match
  - Yellow (60-79): Good match
  - Orange (40-59): Fair match
  - Red (0-39): Poor match
- User can Apply or Dismiss each suggestion

### Data Mutations

**Database Changes**:
- New rows in `jobs` table (all discovered jobs, regardless of score)
- `job_sources.last_scraped_at` updated
- Existing jobs with same URL are skipped (no duplicates)

**Scan Report Structure**:
```json
{
  "sources_scanned": 5,
  "jobs_added": 23,
  "jobs_skipped": 17,
  "skipped_breakdown": {
    "already_existed": 12,
    "low_score": 5  // Note: Low-score jobs are still saved!
  },
  "per_source": [
    {
      "name": "LinkedIn Python Jobs",
      "jobs_added": 8,
      "jobs_skipped": 2
    }
  ]
}
```

### Performance Characteristics

- **Typical scan time (5 sources, 50 jobs total)**: 20-25 seconds
  - Bottlenecks: Slowest source scrape (2-5s) + AI latency (10-15s)
- **Parallelism**: Up to 50 jobs scored concurrently (5 sources × 10 jobs/source)
- **Rate limiting**: 0.2s delay between scraper requests (configurable)

---

## 2. Resume Tailoring Workflow

The resume tailoring workflow converts a generic job suggestion into a customized application with a tailored PDF resume.

### Overview

User clicks "Apply" on a suggested job. The system fetches the full job description, extracts structured requirements using AI, has the AI select and reword the most relevant content from the master resume pool (`data/master_resume.json`) as structured data, renders it to LaTeX via a fixed Jinja2 template, compiles to PDF, and updates job status to `applied`.

### Sequence Diagram

```
User              Frontend           Resume Tailor         Job Scraper        LLM Engine         LaTeX         PostgreSQL
 │                   │                     │                     │                  │             │                │
 │  1. Click "Apply" │                     │                     │                  │             │                │
 │   on Job #42      │                     │                     │                  │             │                │
 ├─────────────────> │                     │                     │                  │             │                │
 │                   │  POST /apply        │                     │                  │             │                │
 │                   │  {url: "..."}       │                     │                  │             │                │
 │                   ├────────────────────>│                     │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │  {status: processing}                     │                  │             │                │
 │                   │<────────────────────┤                     │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │  2. Show "Processing..."                │                     │                  │             │                │
 │<─────────────────  │                     │                     │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  3. Background Task:│                  │             │                │
 │                   │                     │     process_application()              │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  4. Update status   │                  │             │                │
 │                   │                     ├────────────────────────────────────────────────────────────────────>│
 │                   │                     │  UPDATE jobs SET status='processing'   │             │                │
 │                   │                     │    WHERE id=42      │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  5. Fetch full job  │                  │             │                │
 │                   │                     │     description     │                  │             │                │
 │                   │                     ├────────────────────>│                  │             │                │
 │                   │                     │  POST /scrape       │                  │             │                │
 │                   │                     │  {url: "...", wait: 5}                 │             │                │
 │                   │                     │                     │  Fetch HTML      │             │                │
 │                   │                     │                     │  (headless       │             │                │
 │                   │                     │                     │   Chrome)        │             │                │
 │                   │                     │  {html: "<div>...Requirements...</div>"}              │                │
 │                   │                     │<────────────────────┤                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  6. Extract requirements                │             │                │
 │                   │                     │     (JobParsingAgent)                  │             │                │
 │                   │                     ├───────────────────────────────────────>│             │                │
 │                   │                     │  Prompt: "Extract structured requirements             │                │
 │                   │                     │           from this job description"   │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  {requirements: [   │                  │             │                │
 │                   │                     │    "5+ years Python",                  │             │                │
 │                   │                     │    "Deep learning experience",         │             │                │
 │                   │                     │    "PhD preferred"  │                  │             │                │
 │                   │                     │  ]}                 │                  │             │                │
 │                   │                     │<───────────────────────────────────────┤             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  7. Save requirements                  │             │                │
 │                   │                     ├────────────────────────────────────────────────────────────────────>│
 │                   │                     │  UPDATE jobs SET requirements='[...]'  │             │                │
 │                   │                     │    WHERE id=42      │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  8. Tailor resume   │                  │             │                │
 │                   │                     │     (ResumeTailorAgent)                │             │                │
 │                   │                     ├───────────────────────────────────────>│             │                │
 │                   │                     │  Prompt: "Select + reword the most     │             │                │
 │                   │                     │           relevant pool content for    │             │                │
 │                   │                     │           this job (structured JSON)"  │             │                │
 │                   │                     │  Input: master_resume.json pool + job  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  ResumeContent {    │                  │             │                │
 │                   │                     │    experience: [...most relevant...],  │             │                │
 │                   │                     │    projects: [...], skills: [...]      │             │                │
 │                   │                     │  }                  │                  │             │                │
 │                   │                     │<───────────────────────────────────────┤             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  9. Enforce budget +│                  │             │                │
 │                   │                     │     render via Jinja2 template         │             │                │
 │                   │                     │     (render_resume) │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  10. Compile to PDF │                  │             │                │
 │                   │                     ├────────────────────────────────────────────────────>│                │
 │                   │                     │  pdflatex tailored_resume.tex          │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  tailored_resume.pdf│                  │             │                │
 │                   │                     │<────────────────────────────────────────────────────┤                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  11. Save PDF path  │                  │             │                │
 │                   │                     ├────────────────────────────────────────────────────────────────────>│
 │                   │                     │  UPDATE jobs SET    │                  │             │                │
 │                   │                     │    pdf_path='./output/job_42_resume.pdf',              │                │
 │                   │                     │    status='applied' │                  │             │                │
 │                   │                     │    WHERE id=42      │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │                   │                     │  ║ If any step fails:                 ║             │                │
 │                   │                     │  ║ UPDATE jobs SET status='failed',    ║             │                │
 │                   │                     │  ║   error_message='...' WHERE id=42   ║             │                │
 │                   │                     │                     │                  │             │                │
 │  12. Poll for     │                     │                     │                  │             │                │
 │      completion   │  GET /jobs/42       │                     │                  │             │                │
 │                   │  (every 2s)         │                     │                  │             │                │
 │                   ├────────────────────>│                     │                  │             │                │
 │                   │                     │  SELECT * FROM jobs WHERE id=42        │             │                │
 │                   │                     ├────────────────────────────────────────────────────────────────────>│
 │                   │                     │                     │                  │             │                │
 │                   │  {id: 42, status: "applied",             │                  │             │                │
 │                   │   pdf_path: "..."}  │                     │                  │             │                │
 │                   │<────────────────────┤                     │                  │             │                │
 │                   │                     │                     │                  │             │                │
 │  13. Show "Applied"│                     │                     │                  │             │                │
 │      badge        │                     │                     │                  │             │                │
 │<─────────────────  │                     │                     │                  │             │                │
```

### Step-by-Step Explanation

#### Phase 1: Initiation

**Step 1-2: User triggers application**

- User clicks "Apply" button on job suggestion (status=`suggested`)
- Frontend sends `POST /apply` with `{url: "https://example.com/job/12345"}`
- Backend creates background task and returns `{status: "processing"}` immediately
- Frontend shows loading spinner and "Processing..." message

**Why background task?**
- Resume tailoring takes 15-30 seconds (AI calls + PDF compilation)
- Non-blocking response prevents timeout
- User can navigate away and return later

#### Phase 2: Job Description Extraction

**Step 3-4: Mark job as processing**

- Background task begins execution
- Update job status to `processing` in database
- Prevents duplicate applications if user clicks "Apply" twice

**Step 5: Fetch full job description**

- Backend calls `POST scraper:8001/scrape` with full job URL
- Scraper uses Playwright to:
  - Launch headless Chrome
  - Navigate to job URL
  - Wait for JavaScript to render (default: 5 seconds)
  - Return full HTML content
- **Key difference from discovery**: Now scraping *individual job page* (detailed description), not search results

**Step 6-7: Extract structured requirements**

`JobParsingAgent` analyzes the job description HTML:

- **AI Prompt**: "Extract key requirements, qualifications, and responsibilities from this job posting. Return as a structured JSON array."
- **Input**: Full HTML of job page
- **Output**: Array of requirement strings
  ```json
  [
    "5+ years of Python development",
    "Experience with deep learning frameworks (PyTorch, TensorFlow)",
    "PhD in Computer Science or related field preferred",
    "Strong communication skills"
  ]
  ```
- **Saved to database**: `jobs.requirements` column (JSON type)

**Why extract requirements separately?**
- Structured data enables future features (requirement matching, skill gap analysis)
- Provides context for resume tailoring agent
- User can review what AI understood from job posting

#### Phase 3: Resume Tailoring

**Step 8: Generate tailored resume content**

`ResumeTailorAgent` selects and rewords content from the master pool:

- **AI Prompt**: select the most relevant experiences/projects, order by relevance, reword bullets to mirror the job's keywords (truthfully, X-Y-Z style), never fabricate, plain text only
- **Input**:
  - Full master content pool (`data/master_resume.json` loaded as `ResumeContent`)
  - Parsed job posting (company, title, summary, key requirements)
- **Output**: a validated `ResumeContent` object (structured output against the Pydantic schema — never LaTeX)

**Step 9: Enforce budget and render to LaTeX**

- `_enforce_budget()`: restore the header verbatim from the master, cap to 5 experiences / 5 projects / bullet limits for a one-page result
- `render_resume()` (`core/resume_renderer.py`): render the content through the fixed Jinja2 template `data/resume_template.tex.j2`, with every value LaTeX-escaped — the output is always compilable
- Write to `./output/job_42_resume.tex`

#### Phase 4: PDF Compilation

**Step 10: Compile LaTeX to PDF**

- Run `pdflatex` command via subprocess:
  ```bash
  pdflatex -output-directory=./output job_42_resume.tex
  ```
- **Requires TeX Live**: Why this service runs in Docker (60MB+ installation)
- **Failure handling**: If LaTeX is malformed, compilation fails
  - Error logged to `jobs.error_message`
  - Status set to `failed`
  - User sees error in UI

**Step 11: Save PDF path and update status**

- Store PDF location in `jobs.pdf_path`
- Update `jobs.status` to `applied`
- Atomic transaction ensures consistency

#### Phase 5: Completion

**Step 12-13: Frontend polls for completion**

- Every 2 seconds: `GET /jobs/42`
- When `status=applied`, stop polling
- Display green "Applied" badge
- Show "Download PDF" button linked to `/jobs/42/pdf`

### Error Handling

**Possible Failures**:

1. **Scraping fails** (blocked by website, timeout)
   - Status: `failed`
   - Error: "Failed to fetch job description: Timeout after 30s"

2. **AI extraction fails** (malformed HTML, LLM error/timeout)
   - Status: `failed`
   - Error: "Failed to parse job description: ..."

3. **Resume tailoring fails** (LLM output violates the `ResumeContent` schema, LLM timeout)
   - Status: `failed` after `MAX_RETRIES` attempts (retries surface as SSE `RETRY_ATTEMPT` events)
   - Error: validation or provider error message

4. **PDF compilation fails** (TeX Live error)
   - Status: `failed`
   - Error: "pdflatex: Undefined control sequence \invalidcommand"

**All errors are user-visible** in the dashboard with full error messages.

### Data Mutations

**Database Changes**:
- `jobs.status`: `suggested` → `processing` → `applied` (or `failed`)
- `jobs.requirements`: Populated with JSON array
- `jobs.pdf_path`: Set to output file location
- `jobs.error_message`: Set if failure occurs

**File System Changes**:
- New file: `./output/job_42_resume.tex`
- New file: `./output/job_42_resume.pdf`

### Performance Characteristics

- **Total time**: 15-30 seconds
  - Scraping: 2-5s
  - AI parsing: 3-5s
  - AI tailoring: 5-10s
  - PDF compilation: 2-5s
- **Bottleneck**: AI tailoring (largest prompt + response)
- **No parallelism**: Steps are sequential (each depends on previous)

---

## 3. Application Tracking Workflow

The application tracking workflow manages the job status lifecycle from discovery through final outcome.

### Overview

Jobs flow through a state machine from `suggested` to terminal states (`offer`, `rejected`). Users can manually update statuses via the dashboard to track interview progress and outcomes.

### Status Lifecycle Diagram

```
                    ┌──────────────┐
                    │   Discovery  │
                    │   (Scan)     │
                    └──────┬───────┘
                           │
                           ▼
                    ┌─────────────┐
          ┌────────►│  suggested  │◄─────────┐
          │         └──────┬──────┘          │
          │                │                 │
          │   User clicks "Apply"            │
          │                │                 │
          │                ▼                 │
          │         ┌─────────────┐          │
          │         │ processing  │          │
          │         └──────┬──────┘          │
          │                │                 │
          │      Tailoring succeeds          │
          │                │                 │
          │                ▼                 │
          │         ┌─────────────┐          │
          │         │   applied   │──────────┤
          │         └──────┬──────┘          │
          │                │                 │
          │   User updates status            │
          │                │                 │
          │                ▼                 │
          │         ┌─────────────┐          │
          │         │interviewing │          │
          │         └──────┬──────┘          │
          │                │                 │
          │     Interview completes          │
          │                │                 │
          │        ┌───────┴────────┐        │
          │        │                │        │
          │        ▼                ▼        │
          │  ┌──────────┐    ┌──────────┐   │
          │  │ rejected │    │  offer   │   │
          │  └──────────┘    └──────────┘   │
          │   (terminal)      (terminal)    │
          │                                  │
          │         ┌─────────────┐          │
          │         │   failed    │          │
          │         └──────┬──────┘          │
          │                │                 │
          │  User clicks "Retry"             │
          │                └─────────────────┘
          │
          │  User clicks "Dismiss"
          │         │
          │         ▼
          │  ┌─────────────┐
          └──│  dismissed  │
             └─────────────┘
              (terminal)
```

### Status Definitions

| Status | Meaning | Transitions From | Transitions To | User Actions |
|--------|---------|------------------|----------------|--------------|
| **suggested** | AI discovered and scored, awaiting user decision | (initial state) | `processing`, `dismissed` | Apply, Dismiss |
| **processing** | Resume tailoring in progress | `suggested`, `failed` | `applied`, `failed` | (automatic) |
| **applied** | Tailored resume generated, ready to submit | `processing` | `interviewing`, `rejected` | Update status |
| **interviewing** | Application submitted, in interview process | `applied` | `offer`, `rejected` | Update status |
| **offer** | Job offer received (terminal state) | `interviewing` | (none) | - |
| **rejected** | Application rejected (terminal state) | `applied`, `interviewing` | `suggested` (manual reset) | Retry |
| **failed** | Tailoring or scraping failed | `processing` | `suggested` (retry) | Retry |
| **dismissed** | User dismissed suggestion (terminal state) | `suggested` | (none) | - |

### Sequence Diagrams

#### 3.1: Dismissing a Suggestion

```
User                Frontend              Resume Tailor           PostgreSQL
 │                     │                        │                     │
 │  Click "Dismiss"    │                        │                     │
 │   on Job #15        │                        │                     │
 ├────────────────────>│                        │                     │
 │                     │  POST /jobs/15/dismiss │                     │
 │                     ├───────────────────────>│                     │
 │                     │                        │  UPDATE jobs        │
 │                     │                        │    SET status='dismissed'
 │                     │                        │    WHERE id=15      │
 │                     │                        ├────────────────────>│
 │                     │                        │                     │
 │                     │  {status: "dismissed"} │                     │
 │                     │<───────────────────────┤                     │
 │                     │                        │                     │
 │  Job removed from   │                        │                     │
 │  suggestions list   │                        │                     │
 │<────────────────────│                        │                     │
```

**Key Points**:
- Dismissed jobs are **hidden from suggestions list** (frontend filters `WHERE status != 'dismissed'`)
- **Permanent action**: No built-in "undo" (user would need to manually change status in database)
- **Use case**: User knows they don't want this job (location, salary, company)

#### 3.2: Updating Application Status

```
User                Frontend              Resume Tailor           PostgreSQL
 │                     │                        │                     │
 │  Navigate to        │                        │                     │
 │  /dashboard         │                        │                     │
 ├────────────────────>│                        │                     │
 │                     │  GET /jobs             │                     │
 │                     ├───────────────────────>│                     │
 │                     │                        │  SELECT * FROM jobs │
 │                     │                        │    WHERE status IN  │
 │                     │                        │    ('applied', 'interviewing', ...)
 │                     │                        ├────────────────────>│
 │                     │                        │                     │
 │                     │  [{id: 20, status: "applied", ...}, ...]     │
 │                     │<───────────────────────┤                     │
 │                     │                        │                     │
 │  View dashboard     │                        │                     │
 │  with status badges │                        │                     │
 │<────────────────────│                        │                     │
 │                     │                        │                     │
 │  Click status       │                        │                     │
 │  dropdown for       │                        │                     │
 │  Job #20            │                        │                     │
 │                     │                        │                     │
 │  Select             │                        │                     │
 │  "Interviewing"     │                        │                     │
 ├────────────────────>│                        │                     │
 │                     │  PUT /jobs/20          │                     │
 │                     │  {status: "interviewing"}                    │
 │                     ├───────────────────────>│                     │
 │                     │                        │  UPDATE jobs        │
 │                     │                        │    SET status='interviewing'
 │                     │                        │    WHERE id=20      │
 │                     │                        ├────────────────────>│
 │                     │                        │                     │
 │                     │  {status: "interviewing"}                    │
 │                     │<───────────────────────┤                     │
 │                     │                        │                     │
 │  Badge updates to   │                        │                     │
 │  yellow "Interviewing"                       │                     │
 │<────────────────────│                        │                     │
```

**Key Points**:
- Dashboard shows **all jobs except `suggested` and `dismissed`**
- Status badges are color-coded:
  - `applied`: Blue
  - `interviewing`: Yellow
  - `offer`: Green
  - `rejected`: Red
  - `failed`: Orange
- **Manual tracking**: User updates status as they progress through real-world interview process

#### 3.3: Retrying a Failed Application

```
User                Frontend              Resume Tailor           PostgreSQL
 │                     │                        │                     │
 │  Job #25 failed     │                        │                     │
 │  (shown in dashboard│                        │                     │
 │   with error msg)   │                        │                     │
 │                     │                        │                     │
 │  Click "Retry"      │                        │                     │
 ├────────────────────>│                        │                     │
 │                     │  POST /apply           │                     │
 │                     │  {url: "...", job_id: 25}                    │
 │                     ├───────────────────────>│                     │
 │                     │                        │  UPDATE jobs        │
 │                     │                        │    SET status='processing',
 │                     │                        │        error_message=NULL
 │                     │                        │    WHERE id=25      │
 │                     │                        ├────────────────────>│
 │                     │                        │                     │
 │                     │  {status: "processing"}│                     │
 │                     │<───────────────────────┤                     │
 │                     │                        │                     │
 │  Show "Processing..." │                       │                     │
 │<────────────────────│                        │                     │
 │                     │                        │                     │
 │                     │                        │  Background task:   │
 │                     │                        │  Repeat tailoring   │
 │                     │                        │  workflow (steps    │
 │                     │                        │  from Section 2)    │
```

**Key Points**:
- Retry **clears error message** and restarts tailoring workflow
- Same process as initial application (scrape → parse → tailor → compile)
- **Use case**: Temporary failures (API timeout, rate limit, network issue)

### Data Queries

**Frontend Dashboard Query** (`GET /jobs`):
```sql
SELECT * FROM jobs
WHERE status IN ('applied', 'interviewing', 'offer', 'rejected', 'failed')
ORDER BY created_at DESC;
```

**Frontend Suggestions Query** (`GET /suggestions`):
```sql
SELECT * FROM jobs
WHERE status = 'suggested'
ORDER BY score DESC;
```

**Job Details Query** (`GET /jobs/{id}`):
```sql
SELECT * FROM jobs WHERE id = ?;
```

### User Interactions

**Dashboard Features**:
1. **Status Filter Tabs**: "All", "Applied", "Interviewing", "Offers", "Rejected"
2. **Status Update Dropdown**: Change status directly from table row
3. **PDF Download**: Button appears for jobs with `status=applied` and `pdf_path` set
4. **Error Details**: Expandable section for jobs with `status=failed`
5. **Company/Title Search**: Filter jobs by text search
6. **Date Sorting**: Order by application date (newest first)

**Suggestions Features**:
1. **Score Badges**: Color-coded (green/yellow/orange/red)
2. **Source Tags**: Show which source discovered each job
3. **Quick Actions**: Apply (green button), Dismiss (red icon)
4. **Scan Control**: Select sources, trigger refresh, view progress
5. **Last Report**: View detailed results from previous scan

### Performance Characteristics

- **Dashboard Load**: ~50ms (simple SQL query, no AI)
- **Status Update**: ~10ms (single SQL UPDATE)
- **Suggestions Load**: ~100ms (joins with job_sources table)
- **No polling**: Status updates are immediate (no background processing)

---

## Summary

### Three Core Workflows

1. **Job Discovery**: Parallel AI-powered scanning of job sources
   - Input: Source URLs + global filter
   - Output: Suggested jobs with AI scores
   - Time: 20-25 seconds for 5 sources, 50 jobs

2. **Resume Tailoring**: Automated customization of resumes for specific jobs
   - Input: Job URL + master resume
   - Output: Tailored PDF resume
   - Time: 15-30 seconds per job

3. **Application Tracking**: Manual status management through lifecycle
   - Input: User status updates
   - Output: Organized dashboard with stage tracking
   - Time: Instant (no AI involved)

### Data Flow Principles

- **Async by Default**: Long operations (scanning, tailoring) run in background
- **Polling for Progress**: Frontend polls every 2 seconds for status updates
- **All Jobs Saved**: Even low-score suggestions are persisted (user may re-evaluate)
- **Idempotency**: Duplicate URLs are skipped (deduplication on `jobs.url`)
- **Error Transparency**: All failures visible to user with detailed messages

### Parallelism Strategy

- **Source Level**: Up to 5 sources scanned concurrently
- **Job Level**: Up to 10 jobs scored per source concurrently
- **Total Concurrency**: 50 jobs scored in parallel (5 × 10)
- **No Shared State**: Each job's tailoring runs independently

This architecture enables AutoCareer to discover and apply to hundreds of jobs per day while maintaining quality and user control.
