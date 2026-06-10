# Environment Setup

This guide walks you through configuring environment variables for AutoCareer. Proper configuration is essential for AI-powered job discovery, database persistence, and resume tailoring.

## Configuration File

AutoCareer uses a single `.env` file located at the **repository root**:

```
/Users/alexyuan/Documents/job-auto-apply/.env
```

This file is loaded by the `tailor` service (main backend) on startup. The frontend has a separate configuration file described below.

**Important:** Never commit `.env` to version control. It's already in `.gitignore`.

## Required Variables

AutoCareer's AI agents (job discovery, scoring, parsing, resume tailoring) run on **Claude** by default, authenticated with a **Claude Pro/Max subscription** — there is no per-token API billing. Gemini remains available as a legacy fallback.

### CLAUDE_CODE_OAUTH_TOKEN

**Required** (default Claude path) — Authenticates the Claude Agent SDK against your Claude subscription.

```bash
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token_here
```

**How to get your token:**

1. Install the Claude CLI (`@anthropic-ai/claude-code`) on your host machine.
2. Run `claude setup-token` once and complete the browser login with your Claude Pro/Max account.
3. Copy the generated token into your `.env` file as `CLAUDE_CODE_OAUTH_TOKEN`.

Inference is billed against your Claude subscription, so there is no per-token API cost.

> **Never set `ANTHROPIC_API_KEY`.** It shadows `CLAUDE_CODE_OAUTH_TOKEN` and switches billing to pay-per-token. The `tailor` service runs a `claude_auth_configured` startup check that fails fast if `ANTHROPIC_API_KEY` is present.

> **Note:** The `tailor` Docker image installs Node and `@anthropic-ai/claude-code`; the Claude Agent SDK spawns the `claude` CLI as a subprocess, so no separate setup is needed inside the container.

### LLM_PROVIDER

Selects which LLM engine the agents use.

```bash
LLM_PROVIDER=claude  # Options: claude | gemini
```

| Value | Description |
|-------|-------------|
| `claude` | Claude via the Claude Agent SDK (default). Requires `CLAUDE_CODE_OAUTH_TOKEN`. |
| `gemini` | Google Gemini API (legacy fallback). Requires `GOOGLE_API_KEY`. |

### CLAUDE_MODEL

Selects the Claude model used by the agents (only relevant when `LLM_PROVIDER=claude`).

```bash
CLAUDE_MODEL=sonnet  # Options: sonnet (default) | haiku | opus | full model id
```

**Default:** `sonnet`. You may also pass a fully qualified model id.

### GOOGLE_API_KEY

**Required only when `LLM_PROVIDER=gemini`** (legacy fallback) — Powers all AI agents via the Google Gemini API.

```bash
GOOGLE_API_KEY=your_api_key_here
```

**How to get your API key:**

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and paste it into your `.env` file

## Database Configuration

AutoCareer supports three database modes: **hybrid** (recommended), **postgres**, and **sqlite**.

### DATABASE_BACKEND

```bash
DATABASE_BACKEND=hybrid  # Options: postgres | sqlite | hybrid
```

| Mode | Description | Use Case |
|------|-------------|----------|
| `postgres` | PostgreSQL only (container-based) | Production, multi-user access |
| `sqlite` | SQLite only (file-based) | Portable, single-user, offline |
| `hybrid` | Both databases in sync | Best of both worlds (default) |

### Connection Strings

#### PostgreSQL (Used by `postgres` and `hybrid` modes)

```bash
POSTGRES_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer
```

**Format:** `postgresql://[user]:[password]@[host]:[port]/[database]`

**Default credentials** (defined in `docker-compose.yml`):
- Username: `postgres`
- Password: `postgres`
- Host: `postgres` (Docker service name)
- Port: `5432`
- Database: `autocareer`

#### SQLite (Used by `sqlite` and `hybrid` modes)

```bash
SQLITE_DATABASE_URL=sqlite:///./backend/services/resume-tailor/data/autocareer.db
```

**Path:** `./backend/services/resume-tailor/data/autocareer.db` (relative to the `tailor` service working directory inside Docker)

**On host system:** `/Users/alexyuan/Documents/job-auto-apply/backend/services/resume-tailor/data/autocareer.db`

### Hybrid Mode Sync Settings

When `DATABASE_BACKEND=hybrid`, AutoCareer keeps PostgreSQL and SQLite in sync:

```bash
DB_SYNC_ENABLED=true        # Enable bidirectional sync
SYNC_ON_BOOT=true           # Sync PostgreSQL → SQLite on startup
SYNC_ON_SHUTDOWN=true       # Sync SQLite → PostgreSQL on shutdown
```

**Sync behavior:**
- **On boot:** PostgreSQL (source of truth) → SQLite (local copy)
- **During runtime:** All writes go to both databases
- **On shutdown:** SQLite → PostgreSQL (captures any missed writes)

**Why use hybrid mode?**
- PostgreSQL for reliability and backups
- SQLite for portability (copy the `.db` file to another machine)
- Graceful fallback if PostgreSQL is unavailable

### Migration Between Modes

**One-time PostgreSQL → SQLite export:**

```bash
docker-compose exec tailor python /app/scripts/migrate_postgres_to_sqlite.py
```

This script:
1. Reads all data from PostgreSQL
2. Writes to SQLite
3. Preserves IDs, timestamps, and relationships

**Switching from `postgres` to `sqlite`:**

1. Run migration script (above)
2. Change `.env`: `DATABASE_BACKEND=sqlite`
3. Restart services: `docker-compose up --build`

## Service URLs

### SCRAPER_SERVICE_URL

```bash
SCRAPER_SERVICE_URL=http://scraper:8001
```

The `tailor` service calls this URL to fetch job page HTML via headless browser (Playwright).

**Format:** `http://[service_name]:[port]`

**Default:** `scraper:8001` (Docker internal network)

**If running scraper outside Docker:**
```bash
SCRAPER_SERVICE_URL=http://localhost:8001
```

## Resume Content

### MASTER_RESUME_JSON_PATH

```bash
MASTER_RESUME_JSON_PATH=./data/master_resume.json
```

**Path:** Relative to `/app` inside the `tailor` Docker container.

**On host system:** `backend/services/resume-tailor/data/master_resume.json`

**What it is:** your master resume as **structured JSON** — the full pool of header, education, skills, and every experience/project with all bullets. The `ResumeTailorAgent` selects and rewords the most relevant subset per job (validated `ResumeContent`, see `core/resume_model.py`), and `core/resume_renderer.py` renders it to LaTeX via the Jinja2 template `data/resume_template.tex.j2`. The LLM never writes LaTeX.

**Customization:**

1. Edit `master_resume.json` with your experience, skills, education (plain text — special characters are escaped automatically)
2. Layout changes go in `data/resume_template.tex.j2`
3. Restart `tailor` service: `docker-compose restart tailor`

### MASTER_RESUME_PATH (legacy)

```bash
MASTER_RESUME_PATH=./data/master.tex
```

The legacy LaTeX resume. It is **not** used for tailoring anymore — it is kept as the visual reference for the template, and the `master_resume_presence` startup check still verifies it exists.

## Performance Tuning

### RATE_LIMIT_DELAY

```bash
RATE_LIMIT_DELAY=0.2  # Seconds between job page scrapes
```

**Purpose:** Avoid overwhelming job boards (polite scraping).

**Range:** `0.1` (fast, may trigger rate limiting) to `2.0` (very polite, slower scans)

**Default:** `0.2` seconds (5 jobs/second)

### MAX_CONCURRENT_SOURCES

```bash
MAX_CONCURRENT_SOURCES=5  # Max parallel source scans
```

**Purpose:** Process multiple job sources (e.g., LinkedIn, Indeed) simultaneously.

**Range:** `1` (sequential) to `10` (aggressive parallelism)

**Default:** `5` (balanced)

**Trade-off:** Higher values = faster scans, but higher memory usage and API rate limit risk.

### MAX_CONCURRENT_JOBS

```bash
MAX_CONCURRENT_JOBS=10  # Max parallel job scrapes per source
```

**Purpose:** Score multiple job listings from a single source in parallel.

**Range:** `1` (sequential) to `20` (max recommended)

**Default:** `10`

**Trade-off:** Higher values = faster source processing and more concurrent inference load.

## LLM Configuration

The LLM **provider** is selected by [`LLM_PROVIDER`](#llm_provider) (`claude` default, `gemini` fallback). The variable below only toggles stub/offline test modes — it does **not** select the provider.

### RESUME_TAILOR_LLM_MODE

```bash
RESUME_TAILOR_LLM_MODE=  # Options: stub | test | offline (unset = use the real provider)
```

| Mode | Description | Use Case |
|------|-------------|----------|
| _unset_ (or any other value) | Use the real provider chosen by `LLM_PROVIDER` | Production, real AI responses |
| `stub` | Mock responses (hardcoded JSON) | Development, no provider auth needed |
| `test` | Deterministic mock data | Automated testing |
| `offline` | Same as stub | Offline development |

**Example stub mode response:**
```json
{
  "score": 85,
  "reasoning": "Mock scoring response for development"
}
```

**When to use stub/test/offline:**
- Provider authentication not available
- Avoiding inference load during UI development
- Testing error handling with predictable outputs

**Note:** Stub mode jobs will have generic titles/companies like "Software Engineer" / "Tech Corp".

## Frontend Configuration

The Next.js frontend has a separate configuration file:

**Location:** `/Users/alexyuan/Documents/job-auto-apply/frontend/.env.local`

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Purpose:** Tells the frontend where the `tailor` backend API is running.

**Default:** `http://localhost:8000` (Docker exposed port)

**If running backend on a different port:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:9000
```

**In production (same host):**
```bash
NEXT_PUBLIC_API_URL=http://your-domain.com:8000
```

## Complete Example

**`.env` (repository root):**

```bash
# AI Configuration
LLM_PROVIDER=claude
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token_here
CLAUDE_MODEL=sonnet
# RESUME_TAILOR_LLM_MODE is only for stub/test/offline modes; leave unset to use the real provider.

# Legacy Gemini fallback (only used when LLM_PROVIDER=gemini)
# GOOGLE_API_KEY=AIzaSyC1234567890abcdefghijklmnopqrstuvwxyz

# Database Configuration
DATABASE_BACKEND=hybrid
POSTGRES_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer
SQLITE_DATABASE_URL=sqlite:///./backend/services/resume-tailor/data/autocareer.db
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true
SYNC_ON_SHUTDOWN=true

# Service URLs
SCRAPER_SERVICE_URL=http://scraper:8001

# Resume Configuration
MASTER_RESUME_JSON_PATH=./data/master_resume.json   # structured content pool (tailoring/scoring)
MASTER_RESUME_PATH=./data/master.tex                # legacy reference; startup presence check only

# Performance Tuning
RATE_LIMIT_DELAY=0.2
MAX_CONCURRENT_SOURCES=5
MAX_CONCURRENT_JOBS=10
```

**`frontend/.env.local`:**

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Troubleshooting

### Missing or Misconfigured LLM Auth

**Symptom (Claude, default):** the `tailor` startup `claude_auth_configured` check fails, or agents cannot authenticate.

**Solution:**
1. Verify `.env` file exists at repository root
2. Check the token is set: `cat .env | grep CLAUDE_CODE_OAUTH_TOKEN`
3. Ensure `ANTHROPIC_API_KEY` is **not** set — it shadows the OAuth token and is rejected by the startup check: `cat .env | grep ANTHROPIC_API_KEY` (should return nothing)
4. Regenerate the token on the host with `claude setup-token` if needed
5. Restart services: `docker-compose restart tailor`

**Symptom (Gemini fallback):**
```
Error: GOOGLE_API_KEY environment variable not set
```

**Solution:**
1. Confirm `LLM_PROVIDER=gemini` is set
2. Check API key is set: `cat .env | grep GOOGLE_API_KEY`
3. Restart services: `docker-compose restart tailor`

**Alternative:** Use stub mode for development:
```bash
RESUME_TAILOR_LLM_MODE=stub
```

### Database Connection Failed

**Symptom (PostgreSQL):**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solutions:**

1. **Check PostgreSQL is running:**
   ```bash
   docker-compose ps postgres
   ```
   Should show "Up" status.

2. **Verify connection string:**
   ```bash
   echo $POSTGRES_DATABASE_URL
   # Should match: postgresql://postgres:postgres@postgres:5432/autocareer
   ```

3. **Check PostgreSQL logs:**
   ```bash
   docker-compose logs postgres
   ```

4. **Restart PostgreSQL:**
   ```bash
   docker-compose restart postgres
   ```

**Symptom (SQLite):**
```
sqlite3.OperationalError: unable to open database file
```

**Solutions:**

1. **Check directory exists:**
   ```bash
   ls -la backend/services/resume-tailor/data/
   ```

2. **Check file permissions:**
   ```bash
   chmod 644 backend/services/resume-tailor/data/autocareer.db
   ```

3. **Create directory if missing:**
   ```bash
   mkdir -p backend/services/resume-tailor/data
   ```

### Scraper Service URL Not Reachable

**Symptom:**
```
httpx.ConnectError: [Errno 61] Connection refused (scraper:8001)
```

**Solutions:**

1. **Check scraper is running:**
   ```bash
   docker-compose ps scraper
   ```

2. **Verify URL in .env:**
   ```bash
   cat .env | grep SCRAPER_SERVICE_URL
   # Should be: http://scraper:8001
   ```

3. **Test scraper directly:**
   ```bash
   curl -X POST http://localhost:8001/scrape \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com"}'
   ```

4. **Check scraper logs:**
   ```bash
   docker-compose logs scraper
   ```

### Master Resume Not Found

**Symptom:**
```
FileNotFoundError: Master resume JSON not found: ./data/master_resume.json
```
(or `./data/master.tex` from the startup presence check)

**Solutions:**

1. **Verify files exist:**
   ```bash
   ls -la backend/services/resume-tailor/data/master_resume.json
   ls -la backend/services/resume-tailor/data/master.tex
   ```

2. **Check paths in .env:**
   ```bash
   cat .env | grep MASTER_RESUME
   # MASTER_RESUME_JSON_PATH should be: ./data/master_resume.json
   ```

3. **If the JSON fails validation** (Pydantic error on startup/apply): the error names the exact field — see `core/resume_model.py` for the schema constraints (no empty strings, bullets ≤ 400 chars, every experience needs at least one role).

### Frontend Cannot Reach Backend

**Symptom:**
Browser console shows:
```
Failed to fetch http://localhost:8000/jobs
```

**Solutions:**

1. **Check frontend/.env.local exists:**
   ```bash
   cat frontend/.env.local
   # Should contain: NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

2. **Verify backend is running:**
   ```bash
   curl http://localhost:8000/jobs
   ```

3. **Restart frontend:**
   ```bash
   docker-compose restart frontend
   # OR (if running outside Docker):
   cd frontend && npm run dev
   ```

4. **Check CORS settings** (if accessing from different domain):
   Backend `server.py` should have:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Or specify frontend domain
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

---

**Next Steps:**
- [Deployment Guide](deployment.md) — Starting services and health checks
- [Quickstart](quickstart.md) — First job application walkthrough
