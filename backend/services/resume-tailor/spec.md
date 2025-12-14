# Resume Tailor Service Specification

## Goal
A FastAPI microservice that orchestrates the entire resume tailoring workflow: scraping, parsing, tailoring, and compiling.

## 1. System Context

### Architecture
**Dockerized Python 3.11+** environment with bundled TeX Live distribution.
Acts as the primary backend API for the AutoCareer platform.

### Dependencies
*   **Database:** PostgreSQL (via `SQLModel`)
*   **Scraper:** Job Scraper Service (via HTTP)
*   **LLM:** Google Gemini Pro (via `google-genai`)
*   **Compiler:** TeX Live (`pdflatex`)

## 2. Module Specifications

### Module 1: API Server (`server.py`)
**Responsibility:** Entry point for the application.
*   **Endpoints:**
    *   `POST /apply`: Initiates background processing.
    *   `GET /jobs`: Lists jobs.
    *   `GET /jobs/{id}`: Gets job details.
    *   `GET /jobs/{id}/pdf`: Serves generated PDF.
*   **Middleware:** CORS enabled for Frontend communication.
*   **Logging:** Configurable logging levels.

### Module 2: Job Parsing & Scraping
**Responsibility:** Obtaining structured job data.
*   **Scraping:** Delegates to the **Job Scraper Service** (`http://scraper:8001/scrape`).
*   **Parsing:** Uses `JobParsingAgent` (LLM) to extract:
    *   Company Name
    *   Job Title
    *   Key Requirements (List[str])

### Module 3: Resume Tailoring (`core/agents.py`)
**Responsibility:** Adapting the resume content.
*   **Input:** Master Resume (LaTeX) + Job Posting Data.
*   **Process:**
    *   Constructs a prompt for Gemini Pro.
    *   Asks LLM to rewrite specific sections (Summary, Experience) to highlight matching skills.
    *   Ensures LaTeX syntax validity.
*   **Output:** Tailored LaTeX string.

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
*   **Schema:** `Job` table storing metadata and status.

## 3. Configuration
*   `GOOGLE_API_KEY`: Required.
*   `DATABASE_URL`: Postgres connection string.
*   `SCRAPER_SERVICE_URL`: URL of the scraper service.
*   `MASTER_RESUME_PATH`: Path to the template.

