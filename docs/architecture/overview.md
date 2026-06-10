# AutoCareer Architecture Overview

## Introduction

AutoCareer is a self-hosted job application automation platform built on a microservices architecture. The system uses AI to discover relevant jobs, score them against your resume, automatically tailor your resume for each position, and track applications through the entire lifecycle.

The platform emphasizes:
- **Privacy-First Design**: All data stays on your machine, self-hosted
- **AI-Powered Intelligence**: Claude (via the Claude Agent SDK) for discovery, scoring, parsing, and tailoring
- **Parallel Processing**: Concurrent source scanning and job scoring for speed
- **Modularity**: Independent microservices that can scale separately

## Microservices Architecture

AutoCareer consists of 4 Docker Compose services:

| Service | Port | Technology | Responsibility |
|---------|------|------------|----------------|
| **Frontend** | 3000 | Next.js 14, TypeScript, shadcn/ui | Web UI, user interaction, orchestration |
| **Resume Tailor** | 8000 | Python 3.11, FastAPI, SQLModel | Main API, AI agents, business logic, PDF generation |
| **Job Scraper** | 8001 | Python 3.11, FastAPI, Playwright | Headless browser scraping, HTML fetching |
| **PostgreSQL** | 5432 | PostgreSQL 15 | Persistent storage, job data, sources |

**Request Flow:**
```
User Browser → Frontend (3000) → Resume Tailor API (8000) → Job Scraper (8001)
                                         ↓
                                  PostgreSQL (5432)
```

## Service Responsibilities

### Frontend Service (Port 3000)

**Technology**: Next.js 14 with App Router, React 19, TypeScript, Tailwind CSS, shadcn/ui

**Responsibilities**:
- Serve web interface for all user interactions
- Orchestrate API calls to backend services
- Display job suggestions with AI scores
- Manage application tracking dashboard
- Handle source configuration UI
- Poll for long-running job scan status
- Present scan reports with per-source results

**Key Pages**:
- `/dashboard` - Application history with status badges
- `/suggestions` - Job discovery, source management, AI scoring
- `/apply` - Manual URL submission for one-off applications
- `/jobs/[id]` - Job details, requirements, PDF download

**State Management**: React hooks (`useState`, `useEffect`) with polling patterns for async operations

### Resume Tailor Service (Port 8000)

**Technology**: Python 3.11, FastAPI, SQLModel, Alembic, Claude (Claude Agent SDK), TeX Live

**Responsibilities**:
- Serve 14 REST API endpoints for all operations
- Execute 4 AI agents for job discovery, scoring, parsing, tailoring
- Orchestrate parallel source scanning (up to 5 sources concurrently)
- Manage background tasks for resume tailoring
- Compile LaTeX resumes to PDF using TeX Live
- Handle database migrations via Alembic
- Track job lifecycle and application status

**AI Agents** (all use Claude via the Claude Agent SDK, depending only on the `LLMProvider` interface):
1. **JobDiscoveryAgent**: Parse source HTML → extract job listings → apply user filter
2. **JobScoringAgent**: Compare job to resume → return score 0-100
3. **JobParsingAgent**: Extract structured requirements from job description
4. **ResumeTailorAgent**: Select/reword the most relevant subset of the master content pool (`data/master_resume.json`) for a job — structured `ResumeContent` output, rendered to LaTeX deterministically by `core/resume_renderer.py`

**Parallel Processing**:
- `MAX_CONCURRENT_SOURCES=5`: Scan up to 5 job sources simultaneously
- `MAX_CONCURRENT_JOBS=10`: Score up to 10 jobs per source in parallel (thread pool)
- Relative URLs automatically resolved to absolute using source base URL

**API Endpoints**:
- Jobs: `POST /apply`, `GET /jobs`, `GET /jobs/{id}`, `GET /jobs/{id}/pdf`, `POST /jobs/{id}/dismiss`
- Sources: `GET /sources`, `POST /sources`, `PUT /sources/{id}`, `DELETE /sources/{id}`
- Suggestions: `GET /suggestions`, `POST /suggestions/refresh`, `GET /suggestions/status`
- Settings: `GET /settings/global-filter`, `PUT /settings/global-filter`

### Job Scraper Service (Port 8001)

**Technology**: Python 3.11, FastAPI, Playwright (headless Chrome), BeautifulSoup

**Responsibilities**:
- Provide `POST /scrape` endpoint for HTML fetching
- Run headless Chrome browser via Playwright
- Handle JavaScript-rendered content
- Parse HTML with BeautifulSoup
- Support both search pages and full job descriptions
- Rate limiting via `RATE_LIMIT_DELAY=0.2` seconds

**Why Separate Service?**:
- Isolates heavy Chromium dependencies
- Allows independent scaling for scraping workload
- Prevents browser crashes from affecting main API
- Enables headless browser reuse across requests

### PostgreSQL Service (Port 5432)

**Technology**: PostgreSQL 15

**Responsibilities**:
- Persist all job data, sources, and settings
- Support complex queries for job filtering
- Provide ACID guarantees for application tracking
- Enable database migrations via Alembic

**Hybrid Mode Support**:
- Can run in `hybrid` mode with SQLite for portability
- PostgreSQL for primary runtime, SQLite for export/backup
- Migration script available for PostgreSQL → SQLite

## Technology Stack Per Service

### Frontend Stack

| Technology | Purpose |
|------------|---------|
| Next.js 14 (App Router) | React framework with server components, file-based routing |
| React 19 | UI component library with hooks |
| TypeScript | Type safety, better IDE support |
| Tailwind CSS | Utility-first CSS framework |
| shadcn/ui | Pre-built accessible UI components (Button, Card, Badge, Table) |

### Backend Stack (Resume Tailor)

| Technology | Purpose |
|------------|---------|
| Python 3.11 | Modern Python with performance improvements |
| FastAPI | High-performance async API framework with auto-generated docs |
| SQLModel | Combines SQLAlchemy ORM with Pydantic validation |
| Alembic | Database schema migration tool |
| Claude (Claude Agent SDK) | LLM for AI agents with structured output via the SDK's `output_format` JSON schema, validated by Pydantic; selectable via `LLM_PROVIDER` (Gemini fallback) |
| TeX Live (pdflatex) | LaTeX to PDF compilation for resumes |

### Backend Stack (Job Scraper)

| Technology | Purpose |
|------------|---------|
| Playwright | Headless browser automation (supports JavaScript-rendered pages) |
| BeautifulSoup | HTML parsing and extraction |
| FastAPI | Lightweight API server for scraping endpoint |

### Database Stack

| Technology | Purpose |
|------------|---------|
| PostgreSQL 15 | Primary relational database |
| SQLite | Optional hybrid mode for portability |

## Database Schema

### Settings Table

Stores global configuration as key-value pairs.

| Column | Type | Description |
|--------|------|-------------|
| `key` | TEXT (PK) | Setting name (e.g., "global_filter") |
| `value` | TEXT | Setting value (job filter prompt) |
| `updated_at` | TIMESTAMP | Last modification timestamp |

**Example Row**:
```
key: "global_filter"
value: "Software Engineer with 5+ years experience in Python and ML"
```

### JobSource Table

Defines job board URLs to scan for opportunities.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-incrementing ID |
| `url` | TEXT (UNIQUE) | Job board search URL |
| `name` | TEXT | Human-readable name |
| `filter_prompt` | TEXT (nullable) | Source-specific filter (overrides global) |
| `last_scraped_at` | TIMESTAMP (nullable) | Last successful scan time |
| `created_at` | TIMESTAMP | Creation timestamp |

**Example Row**:
```
id: 1
url: "https://www.linkedin.com/jobs/search/?keywords=python"
name: "LinkedIn Python Jobs"
filter_prompt: null  (uses global filter)
last_scraped_at: "2024-01-15T10:30:00Z"
```

### Job Table

Tracks all discovered and applied jobs with their AI scores and status.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER (PK) | Auto-incrementing ID |
| `url` | TEXT (UNIQUE) | Job posting URL (deduplication key) |
| `company` | TEXT | Company name |
| `title` | TEXT | Job title |
| `status` | ENUM | `suggested` \| `processing` \| `applied` \| `interviewing` \| `rejected` \| `offer` \| `failed` \| `dismissed` |
| `score` | INTEGER (nullable) | AI relevance score 0-100 |
| `requirements` | JSON (nullable) | Extracted job requirements as array |
| `error_message` | TEXT (nullable) | Error details if status=failed |
| `pdf_path` | TEXT (nullable) | Path to tailored resume PDF |
| `source_id` | INTEGER (FK, nullable) | Foreign key to JobSource |
| `created_at` | TIMESTAMP | Discovery timestamp |

**Status Lifecycle**:
```
suggested → processing → applied → interviewing → offer
                      ↘ failed                  ↘ rejected
         dismissed (user action)
```

**Example Row**:
```
id: 42
url: "https://careers.example.com/job/12345"
company: "Example Corp"
title: "Senior ML Engineer"
status: "applied"
score: 87
requirements: ["5+ years Python", "Deep learning experience", "PhD preferred"]
pdf_path: "./output/job_42_resume.pdf"
source_id: 1
created_at: "2024-01-15T11:00:00Z"
```

## Complete Directory Structure

This structure follows a **Monorepo pattern** orchestrated by Docker Compose.

```
/job-auto-apply
├── .gitignore
├── docker-compose.yml         # Orchestrates all 4 services
├── package.json               # Root scripts
├── README.md                  # System architecture specification
├── PROJECT_README.md          # Setup and usage instructions
├── FolderStruct.md            # Directory structure documentation
├── CLAUDE.md                  # AI assistant instructions
├── TODO.todo                  # Development tasks
│
├── /docs                      # Documentation
│   ├── /architecture          # Architecture docs (this file)
│   ├── /api                   # API specifications
│   ├── /development           # Development guides
│   ├── /features              # Feature documentation
│   └── /getting-started       # User onboarding
│
├── /frontend                  # Next.js Web Application (Port 3000)
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   │
│   ├── /app                   # Next.js App Router
│   │   ├── layout.tsx         # Root layout with navigation
│   │   ├── page.tsx           # Landing page (redirects to dashboard)
│   │   ├── globals.css        # Global Tailwind styles
│   │   │
│   │   ├── /dashboard         # Application History
│   │   │   └── page.tsx       # Lists applied jobs with status badges
│   │   │
│   │   ├── /apply             # Manual Application Entry
│   │   │   └── page.tsx       # URL submission form for one-off jobs
│   │   │
│   │   ├── /suggestions       # AI Job Discovery (Main Feature)
│   │   │   └── page.tsx       # Source management, scan control, suggestions list
│   │   │
│   │   └── /jobs
│   │       └── /[id]          # Job Details Page
│   │           └── page.tsx   # Requirements, score, PDF download
│   │
│   ├── /components            # React UI Components
│   │   └── /ui                # shadcn/ui primitives
│   │       ├── badge.tsx      # Status and score badges
│   │       ├── button.tsx     # Buttons with variants
│   │       ├── card.tsx       # Card containers
│   │       ├── input.tsx      # Form inputs
│   │       ├── label.tsx      # Form labels
│   │       └── table.tsx      # Data tables
│   │
│   ├── /lib                   # Shared Logic
│   │   ├── api.ts             # Typed API client for all backend endpoints
│   │   └── utils.ts           # Utility functions (cn, formatting)
│   │
│   └── /public                # Static assets
│
└── /backend                   # Python Microservices
    │
    ├── /scripts
    │   ├── seed_jobs.py       # Database seeding utility
    │   └── migrate_postgres_to_sqlite.py  # One-time migration
    │
    └── /services
        │
        ├── /resume-tailor     # Main API Service (Port 8000)
        │   ├── Dockerfile
        │   ├── requirements.txt
        │   ├── server.py      # FastAPI server with 14 endpoints
        │   ├── database.py    # SQLModel ORM (Settings, JobSource, Job)
        │   ├── main.py        # CLI entry point (optional)
        │   ├── spec.md        # OpenAPI specification
        │   ├── README.md      # Service documentation
        │   ├── QUICKSTART.md  # Quick setup guide
        │   ├── .env.example   # Environment template
        │   │
        │   ├── /core          # Business Logic
        │   │   ├── __init__.py
        │   │   ├── agents.py      # 4 AI Agents (Discovery, Scoring, Parsing, Tailoring); depend only on LLMProvider
        │   │   ├── jd_scraper.py  # Job description fetching via scraper service
        │   │   ├── llm_providers.py  # LLMProvider ABC + ClaudeAgentProvider (default), GeminiProvider (fallback), StubProvider; create_default_provider()
        │   │   ├── llm_client.py  # DEPRECATED (not imported) — legacy Gemini HTTP client; see llm_providers.py
        │   │   ├── models.py      # Pydantic data models for AI responses
        │   │   ├── resume_model.py    # ResumeContent schema (structured resume data)
        │   │   ├── resume_renderer.py # Deterministic Jinja2 → LaTeX rendering
        │   │   ├── latex_compiler.py  # pdflatex wrapper for PDF generation
        │   │   └── db_sync.py     # PostgreSQL/SQLite reconciliation
        │   │
        │   ├── /migrations    # Alembic Database Migrations
        │   │   ├── env.py
        │   │   └── /versions
        │   │       ├── 001_initial.py
        │   │       ├── 002_add_job_source.py
        │   │       └── 003_add_settings_table.py
        │   │
        │   ├── /data
        │   │   ├── master_resume.json      # Master resume content pool (source of truth)
        │   │   ├── resume_template.tex.j2  # Jinja2 LaTeX template (Jake Gutierrez layout)
        │   │   ├── master.tex     # Legacy LaTeX resume (visual reference only)
        │   │   └── autocareer.db  # SQLite database (if hybrid mode enabled)
        │   │
        │   └── /output        # Generated PDFs
        │       └── job_*_resume.pdf
        │
        └── /job-scraper       # Scraper Service (Port 8001)
            ├── Dockerfile
            ├── requirements.txt
            ├── main.py        # FastAPI server + Playwright scraper
            └── README.md
```

## Inter-Service Communication

AutoCareer uses HTTP REST APIs for all inter-service communication:

```
┌─────────────────────────────────────────────────────────────────┐
│                          User Browser                            │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Frontend Service (Port 3000)                  │
│                   Next.js + TypeScript + React                   │
│                                                                   │
│  Pages: /dashboard, /suggestions, /apply, /jobs/[id]            │
└────────────────────────────────┬────────────────────────────────┘
                                 │ HTTP REST API
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              Resume Tailor Service (Port 8000)                   │
│                   Python + FastAPI + SQLModel                    │
│                                                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │         AI Agents (Claude via Claude Agent SDK)         │  │
│  │  • JobDiscoveryAgent  • JobScoringAgent                  │  │
│  │  • JobParsingAgent    • ResumeTailorAgent                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                         │                   │                    │
│                         ▼                   ▼                    │
│              ┌──────────────────┐   ┌─────────────────┐         │
│              │  LaTeX Compiler  │   │  Background     │         │
│              │  (TeX Live)      │   │  Task Queue     │         │
│              └──────────────────┘   └─────────────────┘         │
└────────────┬───────────────────────────────────────┬────────────┘
             │ HTTP                                  │ SQL
             ▼                                       ▼
┌─────────────────────────────┐   ┌────────────────────────────────┐
│  Job Scraper (Port 8001)    │   │  PostgreSQL (Port 5432)        │
│  Python + Playwright        │   │                                │
│                             │   │  Tables:                       │
│  ┌───────────────────────┐ │   │  • settings                    │
│  │  Headless Chrome      │ │   │  • job_sources                 │
│  │  (JavaScript Support) │ │   │  • jobs                        │
│  └───────────────────────┘ │   └────────────────────────────────┘
└─────────────────────────────┘

External Services:
  • Claude (via Claude Agent SDK → `claude` CLI subprocess; subscription auth)
  • Job Board Websites (scraping targets)
```

### Communication Patterns

1. **Frontend → Resume Tailor**:
   - REST API calls via `lib/api.ts`
   - Polling for long-running operations (`/suggestions/status`)
   - JSON payloads with TypeScript typing

2. **Resume Tailor → Job Scraper**:
   - `POST /scrape` with URL and wait time
   - Returns HTML content as string
   - Error handling for blocked/failed scrapes

3. **Resume Tailor → PostgreSQL**:
   - SQLModel ORM for all database operations
   - Connection pooling via SQLAlchemy
   - Alembic migrations for schema changes

4. **Resume Tailor → Claude (Claude Agent SDK)**:
   - Calls go through the `LLMProvider` abstraction in `llm_providers.py` (`ClaudeAgentProvider` by default)
   - The SDK shells out to the local `claude` CLI subprocess (Node + `@anthropic-ai/claude-code`)
   - Structured output via the SDK's `output_format` JSON schema → `ResultMessage.structured_output`, validated into Pydantic models in `core/models.py`
   - Subprocess startup makes each call ~3–13s — slower than a direct HTTP path, an accepted trade-off
   - Authenticated by a Claude subscription via `CLAUDE_CODE_OAUTH_TOKEN` (no per-token billing)

### Data Flow Example (Job Discovery)

```
1. User clicks "Refresh Suggestions" in Frontend
   └→ Frontend POST /suggestions/refresh

2. Resume Tailor spawns background task
   └→ For each source in parallel (max 5):
       ├→ POST scraper:8001/scrape (get HTML)
       ├→ JobDiscoveryAgent extracts jobs from HTML
       ├→ Resolve relative URLs to absolute
       └→ For each job in parallel (max 10):
           ├→ JobScoringAgent scores against resume
           └→ INSERT into postgres:5432 (status=suggested)

3. Frontend polls GET /suggestions/status every 2s
   └→ Resume Tailor returns {is_scanning, sources_complete, sources_total}

4. When scan completes:
   └→ Frontend GET /suggestions (fetch new jobs)
   └→ PostgreSQL returns jobs with status=suggested, sorted by score DESC
```

## Key Design Decisions

### Why Microservices?

1. **Independent Scaling**: Scraping is resource-intensive; can scale separately
2. **Fault Isolation**: Browser crashes don't affect main API
3. **Technology Optimization**: Playwright requires headless Chrome; isolated to scraper
4. **Development Velocity**: Teams can work on services independently

### Why PostgreSQL + SQLite Hybrid?

1. **PostgreSQL**: Production-grade reliability, complex queries, ACID guarantees
2. **SQLite**: Portability, easy backups, no external dependencies
3. **Hybrid Mode**: Best of both worlds—develop with SQLite, deploy with PostgreSQL

### Why Claude (subscription)?

1. **No Per-Token Cost**: Inference draws from an existing Claude Pro/Max subscription via `CLAUDE_CODE_OAUTH_TOKEN`, not pay-per-token API billing. Never set `ANTHROPIC_API_KEY` — it shadows the OAuth token and switches to pay-per-token; the `claude_auth_configured` startup check fails fast if it is present.
2. **Structured Output**: The Claude Agent SDK's `output_format` JSON schema yields `structured_output`, validated into Pydantic models — reliable JSON without prompt-engineering.
3. **Provider Abstraction Kept**: Agents depend only on the `LLMProvider` interface in `llm_providers.py`, so Gemini remains a documented fallback (`LLM_PROVIDER=gemini`, needs `GOOGLE_API_KEY`).
4. **Trade-off (Latency)**: The SDK shells out to the `claude` CLI subprocess, so each call is ~3–13s — slower than the old direct Gemini HTTP path. We accept this for the subscription billing model and structured-output reliability.

### Why LaTeX for Resumes?

1. **Professional Typography**: Superior to Word/PDF editors
2. **Version Control**: Plain text, diffs work naturally
3. **Consistency**: Guaranteed identical formatting across jobs

### Why Structured Resume Data (Not LLM-Generated LaTeX)?

1. **Always Compilable**: The LLM produces a validated `ResumeContent` (Pydantic, `core/resume_model.py`); a fixed Jinja2 template (`data/resume_template.tex.j2`) renders it with every value LaTeX-escaped — eliminating the unbalanced-brace/unescaped-character failure class.
2. **Trustworthy Output**: Deterministic guardrails restore the header verbatim and cap content (5 experiences, 5 projects, bullet limits) for a one-page result no matter what the model returns.
3. **One Source of Truth**: `data/master_resume.json` feeds both tailoring and job scoring (via `ResumeContent.to_plain_text()`).

## Performance Characteristics

### Parallel Processing

- **Source Scanning**: 5 sources simultaneously (configurable via `MAX_CONCURRENT_SOURCES`)
- **Job Scoring**: 10 jobs per source in parallel (configurable via `MAX_CONCURRENT_JOBS`)
- **Total Parallelism**: Up to 50 jobs scored concurrently (5 sources × 10 jobs)

### Rate Limiting

- **Scraper Delay**: 0.2 seconds between requests (configurable via `RATE_LIMIT_DELAY`)
- **AI Retry Logic**: Exponential backoff on LLM call failures (handled within the active `LLMProvider`)
- **Browser Reuse**: Playwright keeps Chrome instance alive across requests

### Typical Scan Times

- **Single Source (10 jobs)**: ~15-20 seconds
  - 2s scrape + 10-15s AI scoring (parallel) + 1s database writes
- **5 Sources (50 jobs)**: ~20-25 seconds
  - All sources scanned in parallel
  - Dominated by slowest source + AI latency

## Security Considerations

1. **Self-Hosted**: All data stays on user's machine, no cloud storage
2. **Credentials**: Claude subscription `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) stored in environment variables only; never set `ANTHROPIC_API_KEY` (it shadows the token and enables pay-per-token billing). The Gemini fallback uses `GOOGLE_API_KEY` if `LLM_PROVIDER=gemini`.
3. **No External Webhooks**: No outbound callbacks to third parties
4. **Docker Isolation**: Services run in isolated containers
5. **Database Access**: PostgreSQL not exposed to public internet (port 5432 internal only)

## Future Extensibility

The architecture supports these future enhancements:

1. **Additional AI Providers**: The `LLMProvider` abstraction in `llm_providers.py` makes engines swappable — the Claude migration is already done this way (`ClaudeAgentProvider` default, `GeminiProvider` fallback, `StubProvider` for tests); adding OpenAI or local LLMs is a matter of implementing the interface
2. **More Scrapers**: Add Indeed-specific, LinkedIn-specific scrapers as separate services
3. **Email Integration**: New service for automatic application submission
4. **Mobile App**: Same REST API can serve iOS/Android clients
5. **Multi-User**: Add authentication layer to Resume Tailor service
6. **Analytics**: New service for job market insights, trend analysis
