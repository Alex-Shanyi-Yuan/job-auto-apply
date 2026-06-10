# Resume Tailor Service

The core backend service for AutoCareer - handles AI job discovery, scoring, and resume tailoring.

📚 **Full documentation**: See [docs/](../../../docs/)

## Quick Development Setup

```bash
cd backend/services/resume-tailor
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

```bash
LLM_PROVIDER=claude                              # claude (default) | gemini (legacy fallback)
CLAUDE_CODE_OAUTH_TOKEN=your_subscription_token  # from `claude setup-token`
CLAUDE_MODEL=sonnet                              # sonnet (default) | haiku | opus | full id e.g. claude-sonnet-4-6
DATABASE_BACKEND=hybrid
SQLITE_DATABASE_URL=sqlite:///./data/autocareer.db
POSTGRES_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true
SYNC_ON_SHUTDOWN=true
SCRAPER_SERVICE_URL=http://scraper:8001

# Optional performance tuning
RATE_LIMIT_DELAY=0.2        # Seconds between job scrapes (default: 0.2)
MAX_CONCURRENT_SOURCES=5    # Max parallel source scans (default: 5)
MAX_CONCURRENT_JOBS=10      # Max parallel job scrapes per source (default: 10)
```

The default LLM engine is Claude via the [`claude-agent-sdk`](https://pypi.org/project/claude-agent-sdk/), authenticated by a Claude Pro/Max **subscription** rather than a pay-per-token API key. Generate a token once on the host with `claude setup-token` and put it in `.env` as `CLAUDE_CODE_OAUTH_TOKEN`. Inference then draws from your Claude subscription with no per-token billing.

> **Do not set `ANTHROPIC_API_KEY`** in the tailor process. It shadows `CLAUDE_CODE_OAUTH_TOKEN` and silently switches to pay-per-token billing. The `claude_auth_configured` startup health check fails fast if it is present.

To use the legacy Gemini fallback instead, set `LLM_PROVIDER=gemini` and provide a `GOOGLE_API_KEY` (get one from https://makersuite.google.com/app/apikey).

## API Overview

### Job Discovery & Suggestions

| Endpoint               | Method     | Description              |
| ---------------------- | ---------- | ------------------------ |
| `/sources`             | GET/POST   | Manage job board sources |
| `/sources/{id}`        | PUT/DELETE | Update/delete sources    |
| `/suggestions`         | GET        | List AI-discovered jobs  |
| `/suggestions/refresh` | POST       | Trigger new job scan     |
| `/suggestions/status`  | GET        | Get scan progress        |
| `/health`              | GET        | Startup health check report |

### Resume Tailoring

| Endpoint             | Method | Description            |
| -------------------- | ------ | ---------------------- |
| `/apply`             | POST   | Start resume tailoring |
| `/jobs`              | GET    | List all applied jobs  |
| `/jobs/{id}`         | GET    | Get job details        |
| `/jobs/{id}/stream`  | GET    | Stream live SSE progress for resume tailoring |
| `/jobs/{id}/pdf`     | GET    | Download tailored PDF  |
| `/jobs/{id}/dismiss` | POST   | Dismiss a suggestion   |

### Settings

| Endpoint                  | Method  | Description          |
| ------------------------- | ------- | -------------------- |
| `/settings/global-filter` | GET/PUT | Global filter prompt |

See [spec.md](spec.md) for complete API documentation.

### Startup health checks

On service startup, checks run in this order: database connectivity, migrations baseline, master resume presence, Claude auth (`CLAUDE_CODE_OAUTH_TOKEN` present and `ANTHROPIC_API_KEY` absent) plus `claude` CLI availability, scraper reachability, and pdflatex availability.  
`STARTUP_FAIL_FAST` controls whether critical failures stop startup; `STARTUP_BLOCK_APPLY_ON_CRITICAL` controls whether `POST /apply` is blocked (503) when critical checks fail.

## AI Agents

The service uses four specialized AI agents:

| Agent               | Purpose                                       |
| ------------------- | --------------------------------------------- |
| `JobDiscoveryAgent` | Extracts job listings from search result HTML |
| `JobScoringAgent`   | Scores job-resume match (0-100)               |
| `JobParsingAgent`   | Extracts requirements from job descriptions   |
| `ResumeTailorAgent` | Selects/rewords the most relevant content from the master pool per job (structured `ResumeContent`, never LaTeX) |

All agents call the LLM through `core/llm_providers.py`. Structured output is requested via the SDK's `output_format` JSON schema, returned on `ResultMessage.structured_output`, and validated into the Pydantic models in `core/models.py`.

## Project Structure

```
resume-tailor/
├── core/                      # Core modules
│   ├── agents.py             # AI Agents (Discovery, Scoring, Parsing, Tailoring)
│   ├── jd_scraper.py         # Job description fetching
│   ├── llm_providers.py      # Active LLM layer: LLMProvider ABC + ClaudeAgentProvider (default), GeminiProvider (fallback), StubProvider, create_default_provider()
│   ├── llm_client.py         # DEPRECATED legacy Gemini client (no longer imported; see llm_providers.py)
│   ├── models.py             # Pydantic models for structured LLM output
│   ├── resume_model.py       # ResumeContent schema (structured resume data)
│   ├── resume_renderer.py    # Deterministic Jinja2 → LaTeX rendering
│   └── latex_compiler.py     # PDF compilation
├── migrations/               # Alembic database migrations
│   └── versions/
├── data/
│   ├── master_resume.json    # Your master resume content pool (source of truth)
│   ├── resume_template.tex.j2 # Jinja2 LaTeX template (Jake Gutierrez layout)
│   └── master.tex            # Legacy LaTeX resume (visual reference only)
├── output/                   # Generated PDFs and .tex files
├── server.py                 # FastAPI server (web mode)
├── database.py               # SQLModel database layer
├── main.py                   # CLI entry point
├── requirements.txt
├── Dockerfile
└── README.md
```

## Database Schema

The service supports both PostgreSQL and SQLite with three tables:

- **`settings`**: Key-value store (global filter, etc.)
- **`jobsource`**: Job board search URLs and filters
- **`job`**: Applications with status, score, and PDF paths

Run migrations:

```bash
# Inside the container
alembic upgrade head
```

## Configuration

### Environment Variables

| Variable                | Description                                               | Default                                               |
| ----------------------- | --------------------------------------------------------- | ----------------------------------------------------- |
| `LLM_PROVIDER`          | LLM engine (`claude`, `gemini`)                           | `claude`                                              |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude subscription token from `claude setup-token` (required when `LLM_PROVIDER=claude`) | Required          |
| `CLAUDE_MODEL`          | Claude model (`sonnet`, `haiku`, `opus`, or full id)      | `sonnet`                                              |
| `GOOGLE_API_KEY`        | Gemini API key (required only when `LLM_PROVIDER=gemini`) | —                                                     |
| `DATABASE_BACKEND`      | Active backend (`postgres`, `sqlite`, `hybrid`)           | `postgres`                                            |
| `SQLITE_DATABASE_URL`   | SQLite connection string                                  | `sqlite:///./data/autocareer.db`                      |
| `POSTGRES_DATABASE_URL` | PostgreSQL connection string                              | `postgresql://user:password@postgres:5432/autocareer` |
| `DB_SYNC_ENABLED`       | Enable Postgres/SQLite reconcile                          | `true`                                                |
| `SYNC_ON_BOOT`          | Reconcile at startup when Postgres is reachable           | `true`                                                |
| `SYNC_ON_SHUTDOWN`      | Reconcile at graceful shutdown when Postgres is reachable | `true`                                                |
| `SCRAPER_SERVICE_URL`   | Scraper service URL                                       | `http://scraper:8001`                                 |
| `MASTER_RESUME_JSON_PATH` | Path to the structured master resume pool (tailoring/scoring) | `./data/master_resume.json`                     |
| `MASTER_RESUME_PATH`    | Legacy LaTeX resume (startup presence check only)         | `./data/master.tex`                                   |
| `MAX_RETRIES`           | Retry attempts for tailoring/hook failures                | `3`                                                   |
| `STREAM_QUEUE_WAIT_TIMEOUT_SECONDS` | Max wait for active job stream queue         | `1.0`                                                 |
| `STREAM_QUEUE_WAIT_INTERVAL_SECONDS` | Poll interval while waiting for stream queue   | `0.05`                                                |
| `STARTUP_FAIL_FAST`     | Stop service startup when critical checks fail            | `true`                                                |
| `STARTUP_BLOCK_APPLY_ON_CRITICAL` | Return 503 from `/apply` if critical checks failed | `true`                                           |
| `STARTUP_SCRAPER_TIMEOUT_SECONDS` | Timeout for scraper reachability check         | `5`                                                   |

### One-time PostgreSQL -> SQLite migration

Use this script before switching your runtime backend to SQLite or hybrid mode:

```bash
python backend/scripts/migrate_postgres_to_sqlite.py \
	--postgres-url "postgresql://user:password@localhost:5432/autocareer" \
	--sqlite-url "./backend/services/resume-tailor/data/autocareer.db"
```

The script prints row counts for `settings`, `jobsource`, and `job`, then reports whether counts match after migration.

## CLI Mode (Optional)

You can also run the tailor as a standalone CLI tool:

```bash
# From URL
docker-compose run --rm tailor --url "https://jobs.example.com/posting"

# From file
docker-compose run --rm tailor --file "job_description.txt"

# With custom output name
docker-compose run --rm tailor --url "https://..." --output "GoogleSRE"
```

## Troubleshooting

### "pdflatex not found"

Use Docker - it includes TeX Live automatically.

### "claude CLI not found"

Use Docker - the `tailor` image installs Node.js and `@anthropic-ai/claude-code` so the SDK's `claude` CLI subprocess is available in-container. When running outside Docker, install it with `npm install -g @anthropic-ai/claude-code`.

### "Claude auth not configured" / `claude_auth_configured` check fails

Make sure you created `.env` (not `.env.example`) with a valid `CLAUDE_CODE_OAUTH_TOKEN` (run `claude setup-token` on the host to generate one). Also ensure `ANTHROPIC_API_KEY` is **not** set in the tailor process - it shadows the subscription token and fails this check. If `LLM_PROVIDER=gemini`, set `GOOGLE_API_KEY` instead.

### "LaTeX compilation failed"

Check `output/*.log` for details. Common issues:

- Missing LaTeX packages
- Invalid LaTeX syntax in master resume

### "Failed to fetch URL"

Some sites block scrapers. Save the job description manually and use `--file`.

## Related Documentation

- [API Specification](spec.md) - Complete endpoint documentation
- [Project README](../../../README.md) - Full system architecture
- [Quick Start](QUICKSTART.md) - 5-minute setup guide
