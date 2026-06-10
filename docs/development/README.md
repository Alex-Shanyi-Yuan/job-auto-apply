# Development Guide

This guide covers local development workflows for AutoCareer. For production deployment, see the main [README.md](../../README.md).

## Quick Links

- [Copilot & AI Assistant Setup](./copilot-setup.md)
- [Database Migrations](./database-migrations.md)
- [Testing Strategies](./testing.md)

## Local Development Setup

### Full Stack with Docker (Recommended for First Run)

```bash
# Start all services (frontend, backend, scraper, database)
docker-compose up --build

# View logs
docker-compose logs -f tailor    # Backend
docker-compose logs -f frontend  # Frontend
docker-compose logs -f scraper   # Scraper service
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Scraper: http://localhost:8001

### Running Frontend Outside Docker

**Faster iteration for UI development** — changes auto-reload without rebuilding containers.

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Linting
npm run lint
npm run lint -- --fix
```

**Requirements:**
- Node.js 18+ and npm
- Backend must be running (either in Docker or standalone)

**Configuration:**
Create `frontend/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

The frontend will connect to the backend API on port 8000.

### Running Backend Outside Docker

**Faster iteration for API/agent development** — skip Docker rebuild cycles.

```bash
cd backend/services/resume-tailor

# Create virtual environment (first time only)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run development server with auto-reload
uvicorn server:app --reload --port 8000
```

**Requirements:**
- Python 3.11+
- PostgreSQL or SQLite (see Database Backend below)

**⚠️ PDF Compilation Limitation:**
Resume PDF generation (`latex_compiler.py`) requires TeX Live, which is only installed in the Docker container. If you need to test end-to-end resume tailoring with PDF output, run the `tailor` service in Docker.

**Configuration:**
Create `backend/services/resume-tailor/.env`:
```bash
# LLM engine selection
LLM_PROVIDER=claude                  # claude (default) | gemini (legacy fallback)

# Claude via the claude-agent-sdk, authenticated by a Claude Pro/Max subscription.
# Generate with `claude setup-token`. No per-token API billing.
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token_here
# ⚠️ Do NOT set ANTHROPIC_API_KEY — it shadows the OAuth token and bills pay-per-token.

# Gemini fallback (only required when LLM_PROVIDER=gemini)
GOOGLE_API_KEY=your_gemini_api_key_here

# Database (choose one backend)
DATABASE_BACKEND=sqlite              # sqlite | postgres | hybrid
SQLITE_DATABASE_URL=sqlite:///./data/autocareer.db

# If using PostgreSQL
# POSTGRES_DATABASE_URL=postgresql://user:password@localhost:5432/autocareer

# Scraper service
SCRAPER_SERVICE_URL=http://localhost:8001

# Resume content
MASTER_RESUME_JSON_PATH=./data/master_resume.json   # structured content pool (tailoring/scoring)
MASTER_RESUME_PATH=./data/master.tex                # legacy reference; startup presence check only

# Rate limiting
RATE_LIMIT_DELAY=0.2
MAX_CONCURRENT_SOURCES=5
MAX_CONCURRENT_JOBS=10
```

### Database Backend Options

**SQLite (Default):**
- File-based, no external service required
- Best for local development
- Database stored at `backend/services/resume-tailor/data/autocareer.db`

**PostgreSQL:**
- Run via Docker: `docker-compose up postgres`
- Or install locally and configure connection string

**Hybrid Mode:**
- Syncs between PostgreSQL and SQLite
- See [Database Migrations](./database-migrations.md) for details

### Running Migrations

After pulling schema changes or modifying models:

```bash
# With Docker
docker-compose exec tailor alembic upgrade head

# Without Docker (from backend/services/resume-tailor/)
alembic upgrade head
```

See [Database Migrations](./database-migrations.md) for creating new migrations.

## Code Structure Overview

### Frontend (`frontend/`)

```
frontend/
├── app/                         # Next.js App Router
│   ├── page.tsx                 # Landing page
│   ├── dashboard/page.tsx       # Application history
│   ├── apply/page.tsx           # Manual job submission
│   ├── suggestions/page.tsx     # AI job discovery (main feature)
│   └── jobs/[id]/page.tsx       # Job details
├── components/
│   ├── ui/                      # shadcn/ui components (Button, Card, etc.)
│   └── [custom components]      # Project-specific components
├── lib/
│   └── api.ts                   # Backend API client (all endpoints)
└── public/                      # Static assets
```

**Key Files:**
- `lib/api.ts` — All backend API calls are typed here. **Add new endpoints here first.**
- `app/suggestions/page.tsx` — Most complex UI logic (parallel source scanning, polling, report modal)
- `components/ui/*` — shadcn/ui components (don't modify, regenerate if needed)

**Patterns:**
- State management: `useState` + `useEffect` (no Redux/Zustand)
- API polling: `setInterval` in `useEffect` with cleanup
- Styling: Tailwind CSS utility classes
- Forms: Controlled components with local state

### Backend (`backend/services/resume-tailor/`)

```
backend/services/resume-tailor/
├── server.py                    # FastAPI app (14 endpoints)
├── database.py                  # SQLModel ORM models
├── core/
│   ├── agents.py                # 4 AI agents (Discovery, Scoring, Parsing, Tailoring)
│   ├── llm_providers.py         # LLMProvider ABC + Claude/Gemini/Stub providers + factory
│   ├── llm_client.py            # DEPRECATED legacy Gemini client (not imported)
│   ├── models.py                # Pydantic schemas for structured LLM output
│   ├── resume_model.py          # ResumeContent schema (structured resume data)
│   ├── resume_renderer.py       # Deterministic Jinja2 → LaTeX rendering
│   ├── jd_scraper.py            # Job description fetching (calls scraper service)
│   ├── latex_compiler.py        # PDF generation from LaTeX
│   └── db_sync.py               # PostgreSQL ↔ SQLite sync
├── data/
│   ├── master_resume.json       # Master resume content pool (source of truth)
│   ├── resume_template.tex.j2   # Jinja2 LaTeX template (Jake Gutierrez layout)
│   ├── master.tex               # Legacy LaTeX resume (visual reference only)
│   └── autocareer.db            # SQLite database (if using sqlite backend)
├── migrations/versions/         # Alembic migration scripts
└── scripts/
    └── migrate_postgres_to_sqlite.py  # One-time migration tool
```

**Key Files:**
- `server.py` — All API routes. **Add new endpoints here.**
- `core/agents.py` — AI logic. Each agent returns Pydantic-validated JSON.
- `core/llm_providers.py` — Active LLM layer: the `LLMProvider` ABC plus `ClaudeAgentProvider` (default, via `claude-agent-sdk`), `GeminiProvider` (legacy fallback), `StubProvider` (tests), and the `create_default_provider()` factory.
- `core/llm_client.py` — **Deprecated** legacy Gemini wrapper; no longer imported. Use `core/llm_providers.py`.
- `core/resume_model.py` + `core/resume_renderer.py` — Structured resume pipeline: the tailor agent produces a validated `ResumeContent` (never LaTeX); the renderer turns it into always-compilable LaTeX via `data/resume_template.tex.j2`.
- `database.py` — SQLModel models. **Schema changes require migrations.**

**Patterns:**
- Background tasks: `background_tasks.add_task(function, args)`
- Database sessions: `with Session(engine) as session:`
- AI calls: Always use Pydantic schemas for structured output
- Error handling: Raise `HTTPException` with appropriate status codes

### Scraper Service (`backend/services/job-scraper/`)

```
backend/services/job-scraper/
├── main.py                      # FastAPI app with /scrape endpoint
└── requirements.txt
```

**Purpose:**
- Runs Playwright in headless mode to fetch JavaScript-rendered pages
- Backend calls this service via `SCRAPER_SERVICE_URL`
- Handles bot detection, dynamic content loading

## Testing Workflow

### Frontend Testing

```bash
cd frontend

# Linting
npm run lint

# Type checking
npm run build  # Will fail on TypeScript errors
```

**Manual Testing:**
1. Start backend (Docker or standalone)
2. Run `npm run dev`
3. Navigate to http://localhost:3000
4. Test each page:
   - `/` — Landing page
   - `/suggestions` — Add sources, run scan, review results
   - `/apply` — Submit manual URL
   - `/dashboard` — Check applied jobs
   - `/jobs/[id]` — View job details, download PDF

### Backend Testing

```bash
cd backend/services/resume-tailor

# Run with stub LLM (no API costs)
RESUME_TAILOR_LLM_MODE=stub uvicorn server:app --reload --port 8000

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/suggestions
curl -X POST http://localhost:8000/suggestions/refresh

# Interactive API docs
# Open http://localhost:8000/docs
```

See [Testing Strategies](./testing.md) for AI agent testing with stub mode.

### Integration Testing

```bash
# Full stack
docker-compose up --build

# Verify services
curl http://localhost:8000/health      # Backend
curl http://localhost:8001/health      # Scraper (if exists)
curl http://localhost:3000             # Frontend
```

## Common Development Tasks

### Adding a New API Endpoint

1. **Define endpoint in `server.py`:**
   ```python
   @app.get("/my-endpoint")
   async def my_endpoint():
       return {"message": "Hello"}
   ```

2. **Add client function to `frontend/lib/api.ts`:**
   ```typescript
   export async function myEndpoint() {
     const res = await fetch(`${API_URL}/my-endpoint`);
     return res.json();
   }
   ```

3. **Use in frontend component:**
   ```typescript
   const data = await myEndpoint();
   ```

### Adding a Database Column

1. **Modify model in `database.py`:**
   ```python
   class Job(SQLModel, table=True):
       new_field: Optional[str] = None
   ```

2. **Create migration:**
   ```bash
   docker-compose exec tailor alembic revision --autogenerate -m "add new_field to job"
   ```

3. **Review and apply:**
   ```bash
   # Check migrations/versions/xxxxx_add_new_field_to_job.py
   docker-compose exec tailor alembic upgrade head
   ```

See [Database Migrations](./database-migrations.md) for details.

### Adding a New AI Agent

1. **Define Pydantic schema in `core/agents.py`:**
   ```python
   class MyAgentOutput(BaseModel):
       result: str
   ```

2. **Create agent class:**
   ```python
   from typing import Optional
   from core.llm_providers import LLMProvider, create_default_provider

   class MyAgent:
       def __init__(self, client: Optional[LLMProvider] = None):
           self.client = client or create_default_provider()
       
       async def execute(self, input_data: str) -> MyAgentOutput:
           prompt = f"Process this: {input_data}"
           return await self.client.generate(prompt, MyAgentOutput)
   ```

3. **Call from endpoint:**
   ```python
   agent = MyAgent()                       # uses create_default_provider()
   # agent = MyAgent(client=StubProvider())  # inject a stub in tests
   result = await agent.execute(data)
   ```

### Debugging AI Agents

**Use stub mode to test logic without API costs:**
```bash
RESUME_TAILOR_LLM_MODE=stub uvicorn server:app --reload
```

**Check prompt engineering:**
- Open `core/agents.py`
- Review system prompts and few-shot examples
- Test with real API in small batches

**Monitor LLM usage:**
- Default Claude provider: inference is billed against your Claude Pro/Max subscription (authenticated via `CLAUDE_CODE_OAUTH_TOKEN`), so there is no per-token API cost. Calls run through the `claude` CLI subprocess.
- Legacy Gemini provider (`LLM_PROVIDER=gemini`): check Google Cloud Console → Generative AI Studio for quota limits and costs.

## Contributing Guidelines (Future You)

### Code Style

**Python:**
- Follow PEP 8
- Use type hints for function signatures
- Use Pydantic for data validation
- SQLModel for database models

**TypeScript:**
- Use ESLint rules (run `npm run lint`)
- Prefer functional components with hooks
- Use `async/await` for API calls
- Type API responses

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/my-feature

# Make changes, commit often
git add .
git commit -m "feat: add new feature"

# Before merging, ensure tests pass
npm run lint          # Frontend
docker-compose up -d  # Full stack test

# Merge to main
git checkout main
git merge feature/my-feature
```

### Commit Message Format

Use conventional commits:
- `feat:` — New feature
- `fix:` — Bug fix
- `docs:` — Documentation only
- `refactor:` — Code restructuring
- `test:` — Adding tests
- `chore:` — Tooling, dependencies

### Before Committing

- [ ] Code runs without errors
- [ ] Linting passes (`npm run lint`, `black .`)
- [ ] Database migrations created and tested
- [ ] Environment variables documented
- [ ] Update CLAUDE.md if architecture changes

### Adding Dependencies

**Frontend:**
```bash
cd frontend
npm install package-name
# Commit package.json and package-lock.json
```

**Backend:**
```bash
cd backend/services/resume-tailor
pip install package-name
pip freeze > requirements.txt
# Commit requirements.txt
```

### Documentation Updates

- Update CLAUDE.md for major architectural changes
- Update this guide for new development workflows
- Add inline comments for complex logic only

## Troubleshooting

### Frontend won't start
```bash
# Clear cache and reinstall
cd frontend
rm -rf .next node_modules
npm install
npm run dev
```

### Backend database errors
```bash
# Reset migrations
docker-compose down -v  # ⚠️ Deletes all data
docker-compose up --build

# Or manually
rm backend/services/resume-tailor/data/autocareer.db
docker-compose exec tailor alembic upgrade head
```

### PDF compilation fails
- Ensure TeX Live is installed (only in Docker container)
- Generated LaTeX is always escaped/compilable; check `data/resume_template.tex.j2` if you customized it
- View logs: `docker-compose logs tailor`

### Scraper blocked by website
- Some job sites block headless browsers
- Try different sources
- Check scraper logs: `docker-compose logs scraper`

### API rate limit errors
- Reduce `MAX_CONCURRENT_JOBS` in `.env`
- Increase `RATE_LIMIT_DELAY`
- Use stub mode for testing

## Environment Variables Reference

See `.env.example` in repository root for complete list.

**Critical for development:**
- `LLM_PROVIDER` — `claude` (default) | `gemini` (legacy fallback)
- `CLAUDE_CODE_OAUTH_TOKEN` — Required for the default Claude provider (from `claude setup-token`); billed against your Claude subscription. Do NOT set `ANTHROPIC_API_KEY` (it shadows this and bills per-token).
- `GOOGLE_API_KEY` — Required only when `LLM_PROVIDER=gemini`
- `DATABASE_BACKEND` — sqlite (default) | postgres | hybrid
- `RESUME_TAILOR_LLM_MODE` — Set to `stub`, `test`, or `offline` for testing without invoking the LLM

## Next Steps

- Read [Copilot Setup](./copilot-setup.md) to configure AI assistants
- Review [Database Migrations](./database-migrations.md) before schema changes
- Check [Testing Strategies](./testing.md) for agent testing
