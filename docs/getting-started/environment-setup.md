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

### GOOGLE_API_KEY

**Required** — Powers all AI agents (job discovery, scoring, parsing, resume tailoring).

```bash
GOOGLE_API_KEY=your_api_key_here
```

**How to get your API key:**

1. Visit [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and paste it into your `.env` file

**Note:** Free tier includes 60 requests/minute for Gemini 1.5 Pro. Monitor usage in the AI Studio dashboard.

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

## Resume Template

### MASTER_RESUME_PATH

```bash
MASTER_RESUME_PATH=./data/master.tex
```

**Path:** Relative to `/app` inside the `tailor` Docker container.

**On host system:** `/Users/alexyuan/Documents/job-auto-apply/backend/services/resume-tailor/data/master.tex`

**Template structure:**
- LaTeX format (`.tex` file)
- Sections: `\section{Experience}`, `\section{Education}`, `\section{Skills}`
- The `ResumeTailorAgent` rewrites sections to match job requirements
- Compiled to PDF using TeX Live (installed in Docker image)

**Customization:**

1. Edit `master.tex` with your experience, skills, education
2. Test compilation: `docker-compose exec tailor pdflatex -output-directory=/app/data /app/data/master.tex`
3. Restart `tailor` service: `docker-compose restart tailor`

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

**Trade-off:** Higher values = faster source processing, but higher Gemini API quota consumption.

## LLM Configuration

### RESUME_TAILOR_LLM_MODE

```bash
RESUME_TAILOR_LLM_MODE=gemini  # Options: gemini | stub | test | offline
```

| Mode | Description | Use Case |
|------|-------------|----------|
| `gemini` | Google Gemini API (default) | Production, real AI responses |
| `stub` | Mock responses (hardcoded JSON) | Development, no API key needed |
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
- API key not available
- Avoiding quota consumption during UI development
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
GOOGLE_API_KEY=AIzaSyC1234567890abcdefghijklmnopqrstuvwxyz
RESUME_TAILOR_LLM_MODE=gemini

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
MASTER_RESUME_PATH=./data/master.tex

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

### Missing API Key

**Symptom:**
```
Error: GOOGLE_API_KEY environment variable not set
```

**Solution:**
1. Verify `.env` file exists at repository root
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

### Resume Template Not Found

**Symptom:**
```
FileNotFoundError: [Errno 2] No such file or directory: './data/master.tex'
```

**Solutions:**

1. **Verify file exists:**
   ```bash
   ls -la backend/services/resume-tailor/data/master.tex
   ```

2. **Check path in .env:**
   ```bash
   cat .env | grep MASTER_RESUME_PATH
   # Should be: ./data/master.tex
   ```

3. **Create template if missing:**
   ```bash
   cp backend/services/resume-tailor/data/master.tex.example \
      backend/services/resume-tailor/data/master.tex
   ```

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
