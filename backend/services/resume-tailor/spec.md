# Resume Tailor Service Specification

## Goal
A FastAPI microservice that orchestrates the entire job discovery, scoring, and resume tailoring workflow.

## 1. System Context

### Architecture
**Dockerized Python 3.11+** environment with bundled TeX Live distribution.
Acts as the primary backend API for the AutoCareer platform.

### Dependencies
*   **Database:** PostgreSQL (via `SQLModel` + Alembic migrations)
*   **Scraper:** Job Scraper Service (via HTTP)
*   **LLM:** Google Gemini Pro (via `google-genai`)
*   **Compiler:** TeX Live (`pdflatex`)

## 2. API Endpoints

### Jobs API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/apply` | POST | Start resume tailoring (background task) |
| `/jobs` | GET | List all jobs (excludes suggested/dismissed) |
| `/jobs/{id}` | GET | Get job details |
| `/jobs/{id}/pdf` | GET | Download tailored PDF |
| `/jobs/{id}/dismiss` | POST | Dismiss a suggested job |

### Sources API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/sources` | GET | List all job sources |
| `/sources` | POST | Create a new job source |
| `/sources/{id}` | PUT | Update a job source |
| `/sources/{id}` | DELETE | Delete a job source |

### Suggestions API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/suggestions` | GET | List suggested jobs (sorted by score) |
| `/suggestions/refresh` | POST | Trigger AI job discovery (accepts optional `source_ids` array) |
| `/suggestions/status` | GET | Get scan progress with per-source results |

### Settings API
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/settings/global-filter` | GET | Get global filter prompt |
| `/settings/global-filter` | PUT | Update global filter prompt |

## 3. Module Specifications

### Module 1: API Server (`server.py`)
**Responsibility:** Entry point and API routing.
*   **Middleware:** CORS enabled for Frontend communication.
*   **Background Tasks:** Job discovery and resume tailoring run asynchronously.
*   **Logging:** Configurable logging levels.

### Module 2: AI Agents (`core/agents.py`)
**Responsibility:** LLM-powered intelligence.

| Agent | Purpose |
|-------|---------|
| `JobDiscoveryAgent` | Parses search result HTML to extract job listings |
| `JobScoringAgent` | Scores job-resume match (0-100) |
| `JobParsingAgent` | Extracts structured data from job descriptions |
| `ResumeTailorAgent` | Tailors LaTeX resume to job requirements |

### Module 3: Job Scraping (`core/jd_scraper.py`)
**Responsibility:** Obtaining job data.
*   **Scraping:** Delegates to the **Job Scraper Service** (`http://scraper:8001/scrape`).
*   **HTML Retrieval:** Gets raw HTML for job discovery.

### Module 4: PDF Compilation (`core/latex_compiler.py`)
**Responsibility:** Generating the final asset.
*   **Process:**
    *   Writes tailored LaTeX to a temporary `.tex` file.
    *   Runs `pdflatex` in a subprocess.
    *   Moves output to `output/` directory.
    *   Cleans up auxiliary files (`.log`, `.aux`).
*   **Naming:** Uses sanitized Company Name + Date + UUID to prevent collisions.

### Module 5: Database (`database.py`)
**Responsibility:** Persistence.
*   **ORM:** SQLModel (Pydantic + SQLAlchemy).
*   **Migrations:** Alembic for schema versioning.
*   **Tables:** `settings`, `jobsource`, `job`

## 4. Database Schema

### Settings Table
```sql
CREATE TABLE settings (
    key VARCHAR PRIMARY KEY,
    value TEXT,
    updated_at TIMESTAMP
);
```

### JobSource Table
```sql
CREATE TABLE jobsource (
    id SERIAL PRIMARY KEY,
    url VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    filter_prompt TEXT,          -- Optional source-specific filter
    last_scraped_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Job Table
```sql
CREATE TABLE job (
    id SERIAL PRIMARY KEY,
    url VARCHAR NOT NULL UNIQUE,
    company VARCHAR NOT NULL,
    title VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'processing',  -- processing, applied, interviewing, rejected, offer, failed, suggested, dismissed
    score INTEGER,                         -- AI relevance score 0-100
    requirements JSON,                     -- Extracted requirements list
    error_message VARCHAR,                 -- Error details if failed
    pdf_path VARCHAR,
    source_id INTEGER REFERENCES jobsource(id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

## 5. Configuration
*   `GOOGLE_API_KEY`: Required for Gemini Pro.
*   `DATABASE_URL`: Postgres connection string.
*   `SCRAPER_SERVICE_URL`: URL of the scraper service.
*   `MASTER_RESUME_PATH`: Path to the LaTeX template.

## 6. Job Discovery Flow

1. User configures **Job Sources** (job board search URLs + filter prompts)
2. User sets **Global Filter** (criteria applied to all sources)
3. User clicks **Refresh Suggestions**
4. For each source:
   - Scraper fetches search result HTML
   - `JobDiscoveryAgent` extracts job listings from HTML
   - For each discovered job:
     - `JobScoringAgent` scores relevance (0-100)
     - Job saved with `suggested` status
5. Frontend polls `/suggestions/status` for progress
6. User reviews suggested jobs, clicks **Apply** or **Dismiss**
7. Apply triggers resume tailoring workflow

