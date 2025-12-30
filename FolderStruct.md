# AutoCareer Project Structure

This structure follows a **Monorepo pattern** orchestrated by Docker Compose.

## Top-Level Directory

```
/job-auto-apply
├── .gitignore
├── docker-compose.yml         # Orchestrates all services
├── package.json               # Root scripts
├── README.md                  # System architecture spec
├── PROJECT_README.md          # Setup instructions
├── FolderStruct.md           # This file
│
├── /frontend                  # The "Orchestrator" (Next.js)
│   └── ... (See Section 1)
│
└── /backend                   # The "Workers" (Python)
    └── ... (See Section 2)
```

## 1. Frontend Structure (Next.js)

Located in `/frontend`. Handles the UI and orchestrates calls to the Python backend.

```
/frontend
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.mjs
│
├── /app                       # Next.js App Router
│   ├── layout.tsx             # Root layout
│   ├── page.tsx               # Landing page (redirects to dashboard)
│   ├── globals.css            # Global styles
│   │
│   ├── /dashboard             # Application History
│   │   └── page.tsx           # Lists applied jobs with status badges
│   │
│   ├── /apply                 # Manual Application
│   │   └── page.tsx           # URL submission form
│   │
│   ├── /suggestions           # AI Job Discovery
│   │   └── page.tsx           # Source management, job suggestions, scoring
│   │
│   └── /jobs
│       └── /[id]              # Job Details
│           └── page.tsx       # Requirements, PDF download
│
├── /components                # React UI Components
│   └── /ui                    # shadcn/ui primitives
│       ├── badge.tsx
│       ├── button.tsx
│       ├── card.tsx
│       ├── input.tsx
│       ├── label.tsx
│       └── table.tsx
│
├── /lib                       # Shared Logic
│   ├── api.ts                 # Typed API client for backend
│   └── utils.ts               # Utility functions
│
└── /public                    # Static assets
```

## 2. Backend Structure (Python Microservices)

Located in `/backend`. Split by service for independent scaling.

```
/backend
│
├── /scripts
│   └── seed_jobs.py           # Database seeding utility
│
└── /services
    │
    ├── /resume-tailor         # Main API Service (Port 8000)
    │   ├── Dockerfile
    │   ├── requirements.txt
    │   ├── server.py          # FastAPI server with all endpoints
    │   ├── database.py        # SQLModel ORM (Settings, JobSource, Job)
    │   ├── main.py            # CLI entry point (optional)
    │   ├── spec.md            # API specification
    │   ├── README.md          # Service documentation
    │   ├── QUICKSTART.md      # Quick setup guide
    │   │
    │   ├── /core              # Business Logic
    │   │   ├── __init__.py
    │   │   ├── agents.py      # AI Agents (Discovery, Scoring, Parsing, Tailoring)
    │   │   ├── jd_scraper.py  # Job description fetching
    │   │   ├── llm_client.py  # Gemini API integration
    │   │   ├── models.py      # Pydantic data models
    │   │   └── latex_compiler.py  # PDF compilation
    │   │
    │   ├── /migrations        # Alembic database migrations
    │   │   ├── env.py
    │   │   └── /versions
    │   │       ├── 001_initial.py
    │   │       ├── 002_add_job_source.py
    │   │       └── 003_add_settings_table.py
    │   │
    │   ├── /data
    │   │   └── master.tex     # Master resume template
    │   │
    │   ├── /output            # Generated PDFs
    │   │   └── tailored_resume.tex
    │   │
    │   └── /templates
    │       └── master.tex
    │
    └── /job-scraper           # Scraper Service (Port 8001)
        ├── Dockerfile
        ├── requirements.txt
        ├── main.py            # FastAPI + Playwright scraper
        └── README.md
```

## 3. Docker Services

The `docker-compose.yml` orchestrates three services:

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Next.js web application |
| `tailor` | 8000 | Resume tailor API (Python + TeX Live) |
| `scraper` | 8001 | Headless browser scraper (Playwright) |
| `postgres` | 5432 | PostgreSQL database |

## 4. Key Files

### Configuration
- `docker-compose.yml` - Service orchestration
- `frontend/next.config.ts` - Next.js configuration
- `backend/services/resume-tailor/.env` - API keys and database URL

### Database
- `backend/services/resume-tailor/database.py` - SQLModel models
- `backend/services/resume-tailor/migrations/` - Alembic migrations

### AI Agents
- `backend/services/resume-tailor/core/agents.py` - All AI logic:
  - `JobDiscoveryAgent` - Extracts jobs from search HTML
  - `JobScoringAgent` - Scores relevance 0-100
  - `JobParsingAgent` - Extracts requirements
  - `ResumeTailorAgent` - Rewrites resume

### Frontend API
- `frontend/lib/api.ts` - Typed API client with all endpoints
