# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Knowledge Retention Policy (IMPORTANT)

Documentation updates are part of every change, not a follow-up task. Before finishing
any task that changes code, config, or workflow:

1. Check the Documentation Map below and update every listed doc whose subject you
   changed — in the same commit as the code change.
2. Update this file (CLAUDE.md) when a change affects: services/ports/architecture,
   development commands, code patterns, environment variables, key source files,
   the job status lifecycle, or testing behavior.
3. Grep `docs/` for terms your change made obsolete (renamed files, removed env vars,
   changed defaults) and fix stale mentions.
4. If nothing needs updating, state that explicitly in your summary — decide, don't skip.

Conventions:

- CLAUDE.md is the concise index; `docs/` holds the detail. Never duplicate long
  explanations here.
- `.github/copilot-instructions.md` is a thin pointer at this file — never add project
  knowledge there.
- Design docs are point-in-time records: new ones go in `docs/superpowers/plans/` or
  `specs/` with a date prefix; superseded material moves to `docs/enhancements/archive/`.
  Active docs (`features/`, `architecture/`, `api/`, `getting-started/`, `development/`)
  must always describe the current system.

## Documentation Map

| If you change...                                                       | Also update...                                                                                              |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| API endpoints (`server.py`)                                             | `docs/api/resume-tailor-api.md`; `frontend/lib/api.ts` client                                                |
| Scraper service (`backend/services/job-scraper/`)                       | `docs/api/scraper-api.md`                                                                                    |
| Agents / LLM engine (`core/agents.py`, `core/llm_providers.py`)         | "AI Agents & LLM Engine" here; `docs/features/job-discovery.md` or `resume-tailoring.md`                     |
| Resume pipeline (`resume_model.py`, `resume_renderer.py`, `data/*.j2`)  | "Resume Generation Pipeline" here; `docs/features/resume-tailoring.md`                                       |
| Job discovery / scoring / suggestions scan                              | `docs/features/job-discovery.md`; "Suggestions Scan" here                                                    |
| DB models, migrations, job status lifecycle (`database.py`)             | `docs/development/database-migrations.md`; `docs/features/application-tracking.md`; lifecycle diagram here   |
| Environment variables                                                   | "Environment Variables" here; `docs/getting-started/environment-setup.md`                                    |
| Docker services, ports, deployment (`docker-compose.yml`)               | Architecture table here; `docs/getting-started/deployment.md` + `quickstart.md`                              |
| Test setup / stub mode                                                  | "Testing Gotchas" here; `docs/development/testing.md`                                                        |
| Frontend pages or patterns (`frontend/`)                                | "Frontend Patterns" here; `docs/architecture/data-flow.md` if a flow changes                                 |
| Any new feature                                                         | New file in `docs/features/`; nav link in `docs/README.md`; move roadmap entry in `docs/enhancements/`       |

## Development Commands

```bash
# Start all services
docker-compose up --build

# Frontend only (faster iteration, outside Docker)
cd frontend && npm run dev       # http://localhost:3000
cd frontend && npm run lint      # ESLint

# Run database migrations
docker-compose exec tailor alembic upgrade head

# Create a new migration
docker-compose exec tailor alembic revision --autogenerate -m "description"

# View service logs
docker-compose logs -f tailor
docker-compose logs -f frontend

# Backend (resume-tailor) without Docker
cd backend/services/resume-tailor
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Run the backend test suite (deps live in the repo-root .venv, NOT a per-service venv)
cd backend/services/resume-tailor
TESTING=true /Users/alexyuan/Documents/job-auto-apply/.venv/bin/python -m pytest tests/ -q
```

> Note: PDF compilation (`latex_compiler.py`) requires TeX Live, which is only available in the Docker container. Run `tailor` in Docker when testing resume tailoring end-to-end.

> Note: the LLM engine (Claude) needs the `claude` CLI + a subscription OAuth token. Tests stub the LLM (`StubProvider`), so the suite runs without any token. See "AI Agents & LLM Engine" below.

## Architecture

AutoCareer is a self-hosted job automation platform with 4 Docker Compose services:

| Service    | Port | Stack                                                   | Role                           |
| ---------- | ---- | ------------------------------------------------------- | ------------------------------ |
| `frontend` | 3000 | Next.js 14, React 19, TypeScript, Tailwind, shadcn/ui   | Web UI                         |
| `tailor`   | 8000 | Python 3.11, FastAPI, SQLModel, Claude (Agent SDK), TeX Live | Main API + AI             |
| `scraper`  | 8001 | Python 3.11, FastAPI, Playwright                        | Headless browser for job pages |
| `postgres` | 5432 | PostgreSQL 15                                           | Persistence                    |

**Request flow:** Frontend → `tailor` API (port 8000) → `scraper` service (port 8001) for HTML fetching → PostgreSQL or SQLite depending on `DATABASE_BACKEND`.

### Key Source Files

- `backend/services/resume-tailor/server.py` — All FastAPI endpoints (14 routes)
- `backend/services/resume-tailor/core/agents.py` — 4 AI agents (Discovery, Scoring, Parsing, Tailoring); each depends only on the `LLMProvider` interface
- `backend/services/resume-tailor/core/llm_providers.py` — **The LLM engine.** `LLMProvider` ABC + `ClaudeAgentProvider` (default), `GeminiProvider` (fallback), `StubProvider` (tests), and `create_default_provider()` factory
- `backend/services/resume-tailor/core/models.py` — Pydantic schemas the agents request as structured output: `JobPosting`, `DiscoveredJob`, `DiscoveryResult`, `JobScore`
- `backend/services/resume-tailor/core/resume_model.py` — `ResumeContent` and friends: the structured resume schema (validated, length-constrained) the tailor agent produces
- `backend/services/resume-tailor/core/resume_renderer.py` — `render_resume()`: deterministic Jinja2 → LaTeX rendering with full escaping (the LLM never emits LaTeX)
- `backend/services/resume-tailor/core/startup.py` — Startup health checks (DB, migrations, LLM auth, scraper, pdflatex)
- `backend/services/resume-tailor/database.py` — SQLModel ORM models and backend selection: `Settings`, `JobSource`, `Job`
- `backend/services/resume-tailor/core/db_sync.py` — PostgreSQL/SQLite reconciliation and one-time migration helpers
- `backend/scripts/migrate_postgres_to_sqlite.py` — One-time export from PostgreSQL to SQLite
- `backend/services/job-scraper/main.py` — `POST /scrape` endpoint using Playwright
- `frontend/lib/api.ts` — Typed client for all backend endpoints
- `backend/services/resume-tailor/data/master_resume.json` — **Master resume content pool** (structured JSON, source of truth for tailoring/scoring)
- `backend/services/resume-tailor/data/resume_template.tex.j2` — Jinja2 LaTeX template (Jake Gutierrez layout; `<< >>`/`<% %>` delimiters, `| tex` escape filter)
- `backend/services/resume-tailor/data/master.tex` — Legacy LaTeX resume, kept as visual reference only (still checked by the `master_resume_presence` startup check via `MASTER_RESUME_PATH`)

### Job Status Lifecycle

```
suggested → processing → applied → interviewing → offer
                      ↘ failed                  ↘ rejected
          dismissed (user action)
```

### AI Agents & LLM Engine

Agents never talk to a model SDK directly — they depend on the `LLMProvider` interface in
`core/llm_providers.py` and call `generate_structured(...)` (Pydantic-schema JSON) or
`generate_text(...)`. To change or add a model engine, implement a new `LLMProvider` and wire it
into `create_default_provider()`; **no agent code should change.**

Provider selection (factory in `core/llm_providers.py`):

- `LLM_PROVIDER=claude` (default) → `ClaudeAgentProvider` — runs on a **Claude subscription** via the
  `claude-agent-sdk`, authenticated by `CLAUDE_CODE_OAUTH_TOKEN` (no per-token API billing). The SDK
  shells out to the `claude` CLI subprocess, so calls are heavier/slower than an HTTP API (~3–13s
  each). Structured output uses the SDK's `output_format` json-schema → `ResultMessage.structured_output`.
- `LLM_PROVIDER=gemini` → `GeminiProvider` — legacy fallback, needs `GOOGLE_API_KEY`.
- `RESUME_TAILOR_LLM_MODE` in `{stub,test,offline}` → `StubProvider` — deterministic, used by tests.

> `core/llm_client.py` is a **deprecated** standalone Gemini client and is no longer imported — do not extend it; use `core/llm_providers.py`.

The four agents (all in `core/agents.py`):

1. **JobDiscoveryAgent** — Parses source HTML, extracts job listings, applies user filter
2. **JobScoringAgent** — Scores each discovered job 0–100 against master resume
3. **JobParsingAgent** — Extracts structured requirements from a full job description
4. **ResumeTailorAgent** — Selects/rewords the most relevant subset of the master pool for a specific job (structured output against the `ResumeContent` schema — never raw LaTeX)

### Resume Generation Pipeline

```
data/master_resume.json → ResumeContent (Pydantic, core/resume_model.py)
  → ResumeTailorAgent.tailor(master, job)   # LLM selects/rewords, structured output
  → _enforce_budget()                        # header restored verbatim; hard caps: 5 experiences, 5 projects, 5/3 bullets, 5 skill groups
  → render_resume() (core/resume_renderer.py + data/resume_template.tex.j2)  # deterministic, escaped LaTeX
  → latex_compiler.py → PDF
```

The LLM never writes LaTeX; all values are escaped by the renderer, so output is always compilable. The scoring agent uses the same pool via `ResumeContent.to_plain_text()`.

### Suggestions Scan (Parallel Processing)

`POST /suggestions/refresh` triggers:

1. Parallel source scans (up to `MAX_CONCURRENT_SOURCES=5`)
2. Per source: scraper fetches HTML → `JobDiscoveryAgent` extracts listings → relative URLs resolved to absolute
3. Parallel scoring within each source (up to `MAX_CONCURRENT_JOBS=10` via thread pool)
4. All jobs saved as `status="suggested"` regardless of score
5. Frontend polls `GET /suggestions/status` every 2 seconds until `is_scanning=false`

### Frontend Patterns

- All API calls go through `lib/api.ts` — add new endpoints there
- State: `useState` + `useEffect` (no external state library)
- Polling uses `setInterval` in `useEffect` with cleanup on unmount
- UI uses shadcn/ui components from `components/ui/`

### Backend Patterns

```python
# Background task
background_tasks.add_task(process_application, request.url)

# DB session
with Session(engine) as session:
    job = session.exec(select(Job).where(Job.id == id)).first()
```

## Environment Variables

**Backend** (`.env` at repo root, loaded by `tailor` service):

```
LLM_PROVIDER=claude                 # claude (default) | gemini
CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-...   # Required when LLM_PROVIDER=claude; from `claude setup-token`
CLAUDE_MODEL=sonnet                 # sonnet | haiku | opus | claude-sonnet-4-6 ...
GOOGLE_API_KEY=xxx                  # Required only when LLM_PROVIDER=gemini
DATABASE_BACKEND=hybrid             # postgres | sqlite | hybrid
SQLITE_DATABASE_URL=sqlite:///./backend/services/resume-tailor/data/autocareer.db
POSTGRES_DATABASE_URL=postgresql://user:password@postgres:5432/autocareer
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true
SYNC_ON_SHUTDOWN=true
SCRAPER_SERVICE_URL=http://scraper:8001
MASTER_RESUME_JSON_PATH=./data/master_resume.json   # structured content pool used for tailoring/scoring
MASTER_RESUME_PATH=./data/master.tex                 # legacy reference; only the startup presence check reads it
RATE_LIMIT_DELAY=0.2
MAX_CONCURRENT_SOURCES=5
MAX_CONCURRENT_JOBS=10
```

> **Do not set `ANTHROPIC_API_KEY`** in the `tailor` process — it shadows `CLAUDE_CODE_OAUTH_TOKEN`
> and silently bills pay-per-token instead of the subscription. The `claude_auth_configured` startup
> health check fails fast if it is present.
>
> Generate the token once on the host with `claude setup-token` (requires a Claude Pro/Max plan),
> then put it in `.env`. The Docker image installs Node + `@anthropic-ai/claude-code` so the SDK's
> CLI subprocess exists in-container.

**Frontend** (`frontend/.env.local`):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Database Migrations

Migrations live in `backend/services/resume-tailor/migrations/versions/`. They run automatically on container startup via `entrypoint.sh`. When adding new columns or tables, always create a migration rather than modifying SQLModel models alone.

For hybrid mode or data portability, use `backend/scripts/migrate_postgres_to_sqlite.py` before switching the runtime backend to SQLite.

## Testing Gotchas

- Tests run on the **repo-root `.venv`** (no per-service venv); run with `TESTING=true` to skip DB/lifespan side effects.
- Tests use `StubProvider`, so no Claude/Gemini token is needed to run the suite.
- Scraper is blocked by some job sites — test with different URLs
- AI responses are non-deterministic — verify output quality manually
- Claude calls go through the `claude` CLI subprocess, so each is ~3–13s; a suggestions scan does `1 + N` calls per source — expect scans slower than the old Gemini HTTP path
- Generated LaTeX is always compilable (fixed template + escaping); if pdflatex fails, the bug is in `data/resume_template.tex.j2` — check `docker-compose logs tailor`
