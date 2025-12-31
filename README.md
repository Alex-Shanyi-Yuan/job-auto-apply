# Project Specification: Job Application Automation SaaS ("AutoCareer")

## 1. Executive Summary

**AutoCareer** is a self-hosted SaaS platform designed to automate the job search and application process. It aggregates job postings from configurable sources, uses AI to discover and score relevant jobs, automatically tailors resumes, and tracks the application process via a centralized dashboard.

### Core Value Proposition

* **AI Job Discovery:** Automatically scan job boards and discover relevant opportunities using Google Gemini.
* **Smart Job Scoring:** AI-powered relevance scoring (0-100) based on your resume and preferences.
* **Automated Tailoring:** Rewriting resumes for every single application using Google Gemini Pro.
* **Application Tracking:** Centralized dashboard for all applied roles.
* **Privacy-First:** Self-hosted architecture ensures your data stays on your machine.

## 2. System Architecture (Microservices)

We use a **Microservices Architecture** orchestrated by Docker Compose.

### The "Orchestrator" (Frontend)

**Framework:** Next.js 14 (App Router)
**UI Library:** shadcn/ui + Tailwind CSS
**Port:** `3000`

**Responsibility:**
* User Interface for Dashboard, Job Details, and Suggestions.
* Job Source management (add/edit/delete job boards).
* Triggering AI job discovery and resume tailoring.
* Displaying real-time scan status and progress.

### The "Workers" (Backend Services)

#### Service A: Resume Tailor Service
**Runtime:** Python 3.11 (FastAPI)
**Port:** `8000`
**Responsibility:**
* **API Server:** Handles requests from Frontend.
* **Job Discovery:** AI-powered discovery of jobs from configured sources.
* **Job Scoring:** AI-powered relevance scoring against your resume.
* **Resume Tailoring:** Uses Gemini Pro to rewrite resume sections.
* **PDF Compilation:** Uses `pdflatex` to generate final PDFs.
* **Database Management:** CRUD operations on PostgreSQL.

#### Service B: Job Scraper Service
**Runtime:** Python 3.11 (FastAPI) + Playwright
**Port:** `8001`
**Responsibility:**
* **Headless Browsing:** Renders dynamic JavaScript content.
* **Extraction:** Returns clean text from job URLs.

### The "Persistence" (Database)

**System:** PostgreSQL 15
**Port:** `5432`
**Responsibility:**
* Storing Job Applications, Sources, Settings, and Metadata.
* Data persistence via Docker Volumes.

---

## 3. Detailed Module Specifications

### Module A: Job Scraper Service

**Technology:** Playwright + BeautifulSoup + FastAPI

**Process:**
1. Receives `POST /scrape` with URL.
2. Launches headless Chromium browser.
3. Renders page and extracts raw HTML.
4. Cleans HTML to text using BeautifulSoup.
5. Returns structured JSON `{ title, text, url }`.

### Module B: Resume Tailor Service

**Technology:** FastAPI + SQLModel + Google Gemini + LaTeX

**Core Processes:**

#### Job Discovery Flow
1. **Configure Sources:** User adds job board URLs with optional filter prompts.
2. **Scrape:** Calls Scraper Service to get search result HTML.
3. **Discover:** `JobDiscoveryAgent` uses AI to extract job listings from HTML.
4. **Resolve URLs:** Relative job URLs converted to absolute using source base URL.
5. **Score:** `JobScoringAgent` scores each job (0-100) based on resume fit.
6. **Save:** All jobs saved with `suggested` status (including low-score jobs).
7. **Report:** Detailed per-source results with skip reasons (low_score, already_exists).

**Performance:** Sources and jobs within sources are processed in parallel using asyncio.

#### Resume Tailoring Flow
1. **Apply:** User clicks "Apply" on a suggested job (or submits URL manually).
2. **Scrape:** Calls Module A to get full job description.
3. **Parse:** `JobParsingAgent` extracts requirements from job text.
4. **Tailor:** `ResumeTailorAgent` rewrites resume sections.
5. **Compile:** Generates PDF from tailored LaTeX.
6. **Save:** Updates database with status and PDF path.

### Module C: Frontend Dashboard

**Technology:** Next.js + React + Polling

**Pages:**
1. **Dashboard (`/dashboard`):** Lists all applied jobs with status badges.
2. **Apply (`/apply`):** Manual URL submission form.
3. **Suggestions (`/suggestions`):** AI-discovered jobs with source management.
4. **Job Details (`/jobs/[id]`):** Job metadata, requirements, and PDF download.

---

## 4. Data Model (PostgreSQL)

### Table: `settings`
| Column | Type | Description |
| :--- | :--- | :--- |
| `key` | `String` (PK) | Setting key (e.g., "global_filter") |
| `value` | `Text` | Setting value |
| `updated_at` | `DateTime` | Last modified timestamp |

### Table: `jobsource`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `Integer` (PK) | Unique ID |
| `url` | `String` | Job board search URL |
| `name` | `String` | Display name |
| `filter_prompt` | `Text` (Optional) | Source-specific filter criteria |
| `last_scraped_at` | `DateTime` | Last scan timestamp |
| `created_at` | `DateTime` | Creation timestamp |

### Table: `job`
| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `Integer` (PK) | Unique ID |
| `url` | `String` | Original Job URL |
| `company` | `String` | Company name |
| `title` | `String` | Job title |
| `status` | `Enum` | processing, applied, interviewing, rejected, offer, failed, suggested, dismissed |
| `score` | `Integer` (Optional) | AI relevance score (0-100) |
| `requirements` | `JSON` | Extracted requirements list |
| `error_message` | `String` (Optional) | Error details if failed |
| `pdf_path` | `String` | Path to generated PDF |
| `source_id` | `Integer` (FK) | Reference to JobSource |
| `created_at` | `DateTime` | Creation timestamp |

---

## 5. Access Points

| Service | URL | Purpose |
| :--- | :--- | :--- |
| Frontend | http://localhost:3000 | Web UI |
| Tailor API | http://localhost:8000 | Backend API |
| Scraper API | http://localhost:8001 | Scraping service |
| PostgreSQL | localhost:5432 | Database |

---

## 6. Quick Start

```bash
# Clone and start all services
git clone https://github.com/Alex-Shanyi-Yuan/job-auto-apply.git
cd job-auto-apply
docker-compose up --build

# Open the web UI
open http://localhost:3000
```

See [PROJECT_README.md](PROJECT_README.md) for detailed setup instructions.
| `company` | `String` | Company Name |
| `title` | `String` | Job Title |
| `status` | `String` | `processing`, `applied`, `failed` |
| `requirements` | `JSON` | List of key requirements extracted by AI |
| `pdf_path` | `String` | Path to generated PDF |
| `created_at` | `DateTime` | Timestamp |

---

## 5. Development Workflow

### Prerequisites
* Docker & Docker Compose
* Google Gemini API Key

### Running the Stack
```bash
docker-compose up --build
```

### Access Points
* **Frontend:** http://localhost:3000
* **Tailor API:** http://localhost:8000/docs
* **Scraper API:** http://localhost:8001/docs
* **Database:** localhost:5432 (User: `user`, Pass: `password`, DB: `autocareer`)
