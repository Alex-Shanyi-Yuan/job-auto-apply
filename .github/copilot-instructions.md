# AutoCareer - Copilot Instructions

## Project Overview

AutoCareer is a self-hosted job application automation platform that uses AI to discover, score, and apply to jobs with tailored resumes.

## Architecture

### Services (Docker Compose)

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| `frontend` | 3000 | Next.js 14, TypeScript, shadcn/ui | Web UI |
| `tailor` | 8000 | Python 3.11, FastAPI, SQLModel | Main API, AI agents |
| `scraper` | 8001 | Python 3.11, FastAPI, Playwright | Headless browser scraping |
| `postgres` | 5432 | PostgreSQL 15 | Database |

### Key Directories

```
frontend/
├── app/                    # Next.js App Router pages
│   ├── dashboard/          # Application history
│   ├── apply/              # Manual URL submission
│   ├── suggestions/        # AI job discovery (main feature)
│   └── jobs/[id]/          # Job details
├── components/ui/          # shadcn/ui components
└── lib/api.ts              # Backend API client (all endpoints)

backend/services/resume-tailor/
├── server.py               # FastAPI server (14 endpoints)
├── database.py             # SQLModel models (Settings, JobSource, Job)
├── core/
│   ├── agents.py           # AI Agents (Discovery, Scoring, Parsing, Tailoring) — depend on LLMProvider only
│   ├── llm_providers.py    # LLM engine: LLMProvider ABC + ClaudeAgentProvider (default), GeminiProvider, StubProvider
│   ├── models.py           # Pydantic structured-output schemas (JobPosting, DiscoveredJob, DiscoveryResult, JobScore)
│   ├── resume_model.py     # ResumeContent schema — structured resume data the tailor agent produces
│   ├── resume_renderer.py  # render_resume(): deterministic Jinja2 → LaTeX rendering (LLM never emits LaTeX)
│   ├── startup.py          # Startup health checks (DB, migrations, LLM auth, scraper, pdflatex)
│   ├── llm_client.py       # DEPRECATED standalone Gemini client — not imported, do not extend
│   ├── jd_scraper.py       # Job description fetching
│   └── latex_compiler.py   # PDF generation
├── data/
│   ├── master_resume.json  # Master resume content pool (source of truth for tailoring/scoring)
│   ├── resume_template.tex.j2  # Jinja2 LaTeX template (<< >> / <% %> delimiters, | tex escaping)
│   └── master.tex          # Legacy LaTeX resume, visual reference only
└── migrations/versions/    # Alembic migrations
```

## Database Schema

### Settings Table
- `key` (PK): Setting name (e.g., "global_filter")
- `value`: Setting value
- `updated_at`: Timestamp

### JobSource Table
- `id`, `url`, `name`
- `filter_prompt` (optional): Source-specific filter
- `last_scraped_at`, `created_at`

### Job Table
- `id`, `url` (unique), `company`, `title`
- `status`: processing | applied | interviewing | rejected | offer | failed | suggested | dismissed
- `score` (0-100): AI relevance score
- `requirements`: JSON array of extracted requirements
- `error_message`: Error details if failed
- `pdf_path`, `source_id` (FK), `created_at`

## API Endpoints

### Jobs
- `POST /apply` - Start resume tailoring (background task)
- `GET /jobs` - List applied jobs (excludes suggested/dismissed)
- `GET /jobs/{id}` - Job details
- `GET /jobs/{id}/pdf` - Download PDF
- `POST /jobs/{id}/dismiss` - Dismiss suggestion

### Sources
- `GET /sources` - List sources
- `POST /sources` - Create source
- `PUT /sources/{id}` - Update source
- `DELETE /sources/{id}` - Delete source

### Suggestions
- `GET /suggestions` - List suggested jobs (sorted by score desc)
- `POST /suggestions/refresh` - Trigger AI discovery scan
- `GET /suggestions/status` - Get scan progress

### Settings
- `GET /settings/global-filter` - Get global filter prompt
- `PUT /settings/global-filter` - Update global filter

## AI Agents (core/agents.py)

1. **JobDiscoveryAgent**: Parses search result HTML → extracts job listings (title, company, URL)
2. **JobScoringAgent**: Compares job to resume → returns score 0-100
3. **JobParsingAgent**: Extracts structured requirements from job description
4. **ResumeTailorAgent**: Selects/rewords the most relevant subset of the master pool (`data/master_resume.json`) for a job — structured output against the `ResumeContent` schema, never raw LaTeX. Deterministic guardrails restore the header and cap content to one page; `core/resume_renderer.py` renders the result to always-compilable LaTeX.

All agents depend only on the `LLMProvider` interface in `core/llm_providers.py` (not a model SDK
directly). The default engine is `ClaudeAgentProvider`, which runs on a **Claude subscription** via
`claude-agent-sdk` + `CLAUDE_CODE_OAUTH_TOKEN` (no per-token billing); `GeminiProvider` is a fallback
(`LLM_PROVIDER=gemini`). To swap engines, add an `LLMProvider` and wire it into
`create_default_provider()` — agents stay unchanged.

## Key Workflows

### Job Discovery Flow
1. User configures sources (job board URLs) + global filter
2. Click "Refresh Suggestions" → `POST /suggestions/refresh`
3. Sources are processed in parallel (MAX_CONCURRENT_SOURCES)
4. For each source:
   - Scraper fetches HTML
   - JobDiscoveryAgent extracts jobs (runs in thread pool)
   - Relative URLs resolved to absolute using source base URL
   - Jobs within source scored in parallel (MAX_CONCURRENT_JOBS)
   - JobScoringAgent scores each job (runs in thread pool)
   - Jobs saved with status="suggested" (including low-score jobs)
5. Frontend polls `/suggestions/status` for progress
6. Scan report shows added/skipped jobs with skip reasons

### Resume Tailoring Flow
1. User clicks "Apply" on a job
2. `POST /apply` creates background task
3. Scraper fetches full job description
4. JobParsingAgent extracts requirements
5. ResumeTailorAgent selects/rewords content from `master_resume.json` (structured `ResumeContent`)
6. `render_resume()` renders it to LaTeX; LaTeX compiler generates PDF
7. Job status updated to "applied"

## Frontend Patterns

- **State Management**: React useState + useEffect polling
- **API Client**: `lib/api.ts` with typed functions
- **UI Components**: shadcn/ui (Button, Card, Badge, Input, Label, Table)
- **Styling**: Tailwind CSS

### Suggestions Page Features
- Global filter (purple card) - applied to all sources
- Source management (add/edit/delete) with collapsible section
- Multi-select sources for targeted scanning
- Real-time scan progress panel with parallel source indicators
- Scan report modal with per-source results
  - Added jobs (green) vs Skipped jobs
  - Skip reasons: "Low Score" (orange) vs "Already Existed" (gray)
- Color-coded score badges (green/yellow/orange/red)
- Apply/Dismiss actions with loading states
- "View Last Report" button persists scan results across page refreshes

## Common Patterns

### Backend
```python
# Background task pattern
@app.post("/apply")
async def apply(request: ApplyRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_application, request.url)
    return {"status": "processing"}

# Database session pattern
with Session(engine) as session:
    job = session.exec(select(Job).where(Job.id == id)).first()
```

### Frontend
```typescript
// API call pattern
const [data, setData] = useState<Type[]>([]);
useEffect(() => {
  loadData();
}, []);

async function loadData() {
  const result = await apiFunction();
  setData(result);
}

// Polling pattern
useEffect(() => {
  if (!isScanning) return;
  const interval = setInterval(async () => {
    const status = await getScanStatus();
    if (!status.is_scanning) {
      clearInterval(interval);
      loadData();
    }
  }, 2000);
  return () => clearInterval(interval);
}, [isScanning]);
```

## Environment Variables

### Backend (.env)
```
LLM_PROVIDER=claude          # claude (default) | gemini
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...   # Required for claude; from `claude setup-token`
CLAUDE_MODEL=sonnet          # sonnet | haiku | opus | claude-sonnet-4-6 ...
GOOGLE_API_KEY=xxx           # Required only when LLM_PROVIDER=gemini
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer
SCRAPER_SERVICE_URL=http://scraper:8001
MASTER_RESUME_JSON_PATH=./data/master_resume.json  # structured content pool used for tailoring/scoring
MASTER_RESUME_PATH=./data/master.tex               # legacy reference; only the startup presence check reads it
RATE_LIMIT_DELAY=0.2        # Seconds between job scrapes (default: 0.2)
MAX_CONCURRENT_SOURCES=5    # Max parallel source scans (default: 5)
MAX_CONCURRENT_JOBS=10      # Max parallel job scrapes per source (default: 10)
```
> Never set `ANTHROPIC_API_KEY` — it shadows `CLAUDE_CODE_OAUTH_TOKEN` and bills pay-per-token. The `claude_auth_configured` startup check fails fast if it is present.

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development Commands

```bash
# Start all services (frontend, backend, database)
docker-compose up --build

# Run migrations
docker-compose exec tailor alembic upgrade head

# View logs
docker-compose logs -f tailor
docker-compose logs -f frontend

# Frontend dev (outside Docker, for faster iteration)
cd frontend && npm run dev
```

## Testing Notes

- Run the suite from the repo-root `.venv` with `TESTING=true`; tests use `StubProvider`, so no LLM token is required:
  `cd backend/services/resume-tailor && TESTING=true ../../../.venv/bin/python -m pytest tests/ -q`
- Scraper may be blocked by some job sites - test with different URLs
- AI responses are non-deterministic - verify output quality
- Claude calls run via the `claude` CLI subprocess (~3–13s each), so scans are slower than the old Gemini HTTP path
- Generated LaTeX is always compilable (fixed template + escaping); pdflatex failures point at `data/resume_template.tex.j2` - check logs on failure
