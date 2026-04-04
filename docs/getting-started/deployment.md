# Deployment Guide

This guide covers deploying AutoCareer locally using Docker Compose. All services run in containers for consistent, isolated environments.

## Docker Architecture

AutoCareer consists of 4 services defined in `docker-compose.yml`:

| Service | Port | Technology | Role | Dependencies |
|---------|------|------------|------|--------------|
| **frontend** | 3000 | Next.js 14, React 19 | Web UI | tailor |
| **tailor** | 8000 | Python 3.11, FastAPI | Main API + AI agents | postgres, scraper |
| **scraper** | 8001 | Python 3.11, Playwright | Headless browser | None |
| **postgres** | 5432 | PostgreSQL 15 | Database | None |

**Request flow:**
```
User → frontend:3000 → tailor:8000 → scraper:8001
                              ↓
                         postgres:5432
```

**Networking:**
- All services connected via Docker internal network (`autocareer_default`)
- Exposed ports: `3000`, `8000`, `8001`, `5432` (accessible on `localhost`)

**Volumes:**
- `postgres-data`: PostgreSQL data persistence
- `./backend/services/resume-tailor/data`: Resume templates, SQLite DB, generated PDFs
- `./backend/services/resume-tailor/migrations`: Alembic migration scripts

## Starting Services

### First-Time Setup

1. **Verify prerequisites:**
   ```bash
   docker --version       # Docker 20.10+ required
   docker-compose --version  # Docker Compose 1.29+ or Docker Compose V2
   ```

2. **Create environment files:**
   ```bash
   # Copy example (if provided) or create manually
   cp .env.example .env
   vi .env  # Add your GOOGLE_API_KEY
   
   # Frontend config
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local
   ```

3. **Start all services:**
   ```bash
   docker-compose up --build
   ```

   **What happens:**
   - Downloads base images (Node, Python, PostgreSQL)
   - Builds `frontend`, `tailor`, `scraper` images
   - Creates `postgres-data` volume
   - Runs database migrations (`alembic upgrade head`)
   - Starts all services in attached mode (logs visible)

4. **Wait for services to be ready:**
   ```
   ✓ postgres    | database system is ready to accept connections
   ✓ scraper     | Uvicorn running on http://0.0.0.0:8001
   ✓ tailor      | Uvicorn running on http://0.0.0.0:8000
   ✓ frontend    | Ready started server on 0.0.0.0:3000
   ```

5. **Access the application:**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000/docs (Swagger UI)
   - Scraper: http://localhost:8001/docs

### Subsequent Starts

**Detached mode (recommended for daily use):**
```bash
docker-compose up -d
```

Services run in the background. View logs:
```bash
docker-compose logs -f          # All services
docker-compose logs -f tailor   # Specific service
```

**Quick start (no rebuild):**
```bash
docker-compose start
```

Use when images are already built and no code changes were made.

### Development Mode

**Frontend hot-reload (outside Docker):**
```bash
cd frontend
npm install           # First time only
npm run dev           # http://localhost:3000
```

**Benefits:**
- Faster iteration (no Docker rebuild)
- Instant code changes
- Still uses backend services from Docker

**Note:** Ensure `frontend/.env.local` points to `http://localhost:8000`.

## Stopping Services

### Graceful Shutdown

**Stop all services (containers remain):**
```bash
docker-compose stop
```

**Stop and remove containers:**
```bash
docker-compose down
```

**Stop, remove containers, and delete volumes:**
```bash
docker-compose down -v
```

⚠️ **Warning:** `-v` flag deletes PostgreSQL data. Only use for clean slate.

### Emergency Shutdown

**Force stop (if services are unresponsive):**
```bash
docker-compose kill
docker-compose rm -f
```

## Health Checks

### Service Status

**Check all services:**
```bash
docker-compose ps
```

**Expected output:**
```
NAME                 STATUS    PORTS
frontend             Up        0.0.0.0:3000->3000/tcp
tailor               Up        0.0.0.0:8000->8000/tcp
scraper              Up        0.0.0.0:8001->8001/tcp
postgres             Up        0.0.0.0:5432->5432/tcp
```

**Check individual service:**
```bash
docker-compose ps tailor
```

### API Endpoints

**Tailor (backend) health:**
```bash
curl http://localhost:8000/jobs
# Expected: [] or [...] (JSON array)
```

**Scraper health:**
```bash
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
# Expected: {"html": "..."}
```

**Frontend health:**
```bash
curl http://localhost:3000
# Expected: HTML page
```

**PostgreSQL connection:**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c "SELECT COUNT(*) FROM jobs;"
# Expected: count integer
```

### Service Logs

**View recent logs:**
```bash
docker-compose logs --tail=50 tailor
docker-compose logs --tail=50 scraper
docker-compose logs --tail=50 frontend
docker-compose logs --tail=50 postgres
```

**Follow logs in real-time:**
```bash
docker-compose logs -f tailor
```

**Search logs for errors:**
```bash
docker-compose logs tailor | grep -i error
docker-compose logs tailor | grep -i exception
```

## Database Management

### Migrations

**Run migrations (auto-runs on startup):**
```bash
docker-compose exec tailor alembic upgrade head
```

**Create new migration:**
```bash
docker-compose exec tailor alembic revision --autogenerate -m "Add new column"
```

**Rollback last migration:**
```bash
docker-compose exec tailor alembic downgrade -1
```

**Check current migration:**
```bash
docker-compose exec tailor alembic current
```

**View migration history:**
```bash
docker-compose exec tailor alembic history
```

### PostgreSQL Access

**Interactive SQL shell:**
```bash
docker-compose exec postgres psql -U postgres -d autocareer
```

**Run SQL query:**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c "SELECT * FROM jobs LIMIT 5;"
```

**List all tables:**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c "\dt"
```

**Describe table schema:**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c "\d jobs"
```

### Backup and Restore

**Backup PostgreSQL (SQL dump):**
```bash
docker-compose exec postgres pg_dump -U postgres autocareer > backup_$(date +%Y%m%d).sql
```

**Restore from backup:**
```bash
cat backup_20240404.sql | docker-compose exec -T postgres psql -U postgres -d autocareer
```

**Backup SQLite (file copy):**
```bash
cp backend/services/resume-tailor/data/autocareer.db autocareer_backup_$(date +%Y%m%d).db
```

**Restore SQLite:**
```bash
cp autocareer_backup_20240404.db backend/services/resume-tailor/data/autocareer.db
docker-compose restart tailor
```

**Sync PostgreSQL → SQLite:**
```bash
docker-compose exec tailor python /app/scripts/migrate_postgres_to_sqlite.py
```

## Troubleshooting

### Port Conflicts

**Symptom:**
```
Error: bind: address already in use
```

**Diagnosis:**
```bash
lsof -i :3000  # Check port 3000
lsof -i :8000  # Check port 8000
lsof -i :8001  # Check port 8001
lsof -i :5432  # Check port 5432
```

**Solution 1 — Kill conflicting process:**
```bash
kill -9 <PID>
```

**Solution 2 — Change ports in docker-compose.yml:**
```yaml
services:
  frontend:
    ports:
      - "3001:3000"  # Change 3000 → 3001
  tailor:
    ports:
      - "8002:8000"  # Change 8000 → 8002
```

Update `frontend/.env.local`:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8002
```

### Missing Environment Variables

**Symptom:**
```
tailor | Error: GOOGLE_API_KEY environment variable not set
```

**Solution:**
1. Check `.env` file exists at repository root
2. Verify variable is set:
   ```bash
   cat .env | grep GOOGLE_API_KEY
   ```
3. Restart service:
   ```bash
   docker-compose restart tailor
   ```

**Debugging:**
```bash
# Check if env var is visible inside container
docker-compose exec tailor env | grep GOOGLE_API_KEY
```

### Database Connection Failed

**Symptom:**
```
tailor | sqlalchemy.exc.OperationalError: could not connect to server
```

**Diagnosis:**
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection manually
docker-compose exec postgres psql -U postgres -d autocareer -c "SELECT 1;"
```

**Solution 1 — Restart PostgreSQL:**
```bash
docker-compose restart postgres
docker-compose restart tailor
```

**Solution 2 — Recreate PostgreSQL:**
```bash
docker-compose down
docker-compose up -d postgres
# Wait 10 seconds
docker-compose up -d
```

**Solution 3 — Check connection string:**
```bash
cat .env | grep POSTGRES_DATABASE_URL
# Should be: postgresql://postgres:postgres@postgres:5432/autocareer
```

### Docker Build Failed

**Symptom:**
```
ERROR [internal] load metadata for docker.io/library/node:18-alpine
```

**Solution 1 — Check internet connection:**
```bash
ping docker.io
```

**Solution 2 — Clean Docker cache:**
```bash
docker-compose down
docker system prune -a  # Warning: removes all unused images
docker-compose up --build
```

**Solution 3 — Pull base images manually:**
```bash
docker pull node:18-alpine
docker pull python:3.11-slim
docker pull postgres:15
```

**Symptom:**
```
npm ERR! network request to https://registry.npmjs.org failed
```

**Solution:**
```bash
# Clear npm cache inside container
docker-compose build --no-cache frontend
```

### Frontend Not Loading

**Symptom:**
Browser shows "This site can't be reached" at http://localhost:3000

**Diagnosis:**
```bash
# Check frontend is running
docker-compose ps frontend

# Check frontend logs
docker-compose logs frontend

# Test from command line
curl http://localhost:3000
```

**Solution 1 — Restart frontend:**
```bash
docker-compose restart frontend
```

**Solution 2 — Check frontend is bound to 0.0.0.0:**
```bash
docker-compose logs frontend | grep "started server"
# Should show: started server on 0.0.0.0:3000
```

**Solution 3 — Rebuild frontend:**
```bash
docker-compose up --build frontend
```

### Jobs Not Being Discovered

**Symptom:**
`POST /suggestions/refresh` returns `{"is_scanning": true}` but no jobs appear.

**Diagnosis:**
```bash
# Check tailor logs during scan
docker-compose logs -f tailor

# Check scraper logs
docker-compose logs -f scraper

# Verify sources exist
curl http://localhost:8000/sources
```

**Solution 1 — Check scraper is reachable:**
```bash
docker-compose exec tailor curl http://scraper:8001/scrape -X POST \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Solution 2 — Check GOOGLE_API_KEY:**
```bash
docker-compose exec tailor env | grep GOOGLE_API_KEY
```

**Solution 3 — Reduce concurrency (if rate limited):**
```bash
# In .env:
MAX_CONCURRENT_SOURCES=2
MAX_CONCURRENT_JOBS=5
RATE_LIMIT_DELAY=1.0
```

**Solution 4 — Check job board isn't blocking:**
```bash
# Test scraping manually
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jobs.example.com"}' | jq -r .html
```

### PDF Generation Failed

**Symptom:**
```
tailor | Error: pdflatex command not found
```

**Solution:**
```bash
# Rebuild tailor with TeX Live
docker-compose build --no-cache tailor
docker-compose up -d
```

**Symptom:**
```
tailor | ! LaTeX Error: File 'article.cls' not found
```

**Diagnosis:**
```bash
# Check TeX Live installation
docker-compose exec tailor which pdflatex
docker-compose exec tailor pdflatex --version
```

**Solution:**
Ensure `Dockerfile` for `tailor` includes:
```dockerfile
RUN apt-get update && apt-get install -y \
    texlive-latex-base \
    texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*
```

**Symptom:**
```
tailor | ! Undefined control sequence. \section{Experience}
```

**Solution:**
Check `master.tex` syntax:
```bash
docker-compose exec tailor pdflatex -interaction=nonstopmode \
  -output-directory=/app/data /app/data/master.tex
```

Fix LaTeX errors in `backend/services/resume-tailor/data/master.tex`.

### High Memory Usage

**Symptom:**
System becomes slow, Docker shows high memory consumption.

**Diagnosis:**
```bash
docker stats
```

**Solution 1 — Reduce concurrency:**
```bash
# In .env:
MAX_CONCURRENT_SOURCES=2
MAX_CONCURRENT_JOBS=5
```

**Solution 2 — Limit Docker memory:**
Edit `docker-compose.yml`:
```yaml
services:
  tailor:
    deploy:
      resources:
        limits:
          memory: 2G
  frontend:
    deploy:
      resources:
        limits:
          memory: 1G
```

**Solution 3 — Clean up Docker:**
```bash
docker system prune -a --volumes
# Warning: removes all unused containers, images, volumes
```

### Scraper Blocked by Job Boards

**Symptom:**
```
tailor | Error: Scraper returned 403 Forbidden
```

**Diagnosis:**
```bash
# Test scraping directly
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://jobs.example.com"}' | jq -r .html | grep -i "captcha\|blocked"
```

**Solution 1 — Increase rate limit delay:**
```bash
# In .env:
RATE_LIMIT_DELAY=2.0  # 2 seconds between requests
```

**Solution 2 — Rotate user agents:**
Update `backend/services/job-scraper/main.py` to randomize User-Agent headers.

**Solution 3 — Use different job sources:**
Some job boards are more permissive than others. Test with:
- LinkedIn Jobs
- Glassdoor
- Indeed
- Company career pages

## Performance Tips

### Speed Up Scans

1. **Increase concurrency (if resources allow):**
   ```bash
   MAX_CONCURRENT_SOURCES=10
   MAX_CONCURRENT_JOBS=20
   ```

2. **Reduce rate limit delay:**
   ```bash
   RATE_LIMIT_DELAY=0.1
   ```

3. **Use PostgreSQL only (skip hybrid sync overhead):**
   ```bash
   DATABASE_BACKEND=postgres
   ```

### Reduce API Quota Usage

1. **Lower concurrency:**
   ```bash
   MAX_CONCURRENT_JOBS=5
   ```

2. **Use stub mode for testing:**
   ```bash
   RESUME_TAILOR_LLM_MODE=stub
   ```

3. **Scan fewer sources at once:**
   Use multi-select in frontend to scan 1-2 sources instead of all.

### Optimize Database

**PostgreSQL vacuum (reclaim space):**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c "VACUUM ANALYZE;"
```

**Add indexes (if queries are slow):**
```bash
docker-compose exec postgres psql -U postgres -d autocareer -c \
  "CREATE INDEX idx_jobs_status ON jobs(status);"
```

**Clean up old jobs:**
```sql
DELETE FROM jobs WHERE status = 'dismissed' AND created_at < NOW() - INTERVAL '30 days';
```

## Rebuilding After Changes

### Code Changes

**Backend (tailor or scraper):**
```bash
docker-compose up --build tailor
# OR
docker-compose up --build scraper
```

**Frontend:**
```bash
docker-compose up --build frontend
```

**All services:**
```bash
docker-compose up --build
```

### Dependency Changes

**Python requirements:**
```bash
docker-compose build --no-cache tailor
docker-compose up -d
```

**Node packages:**
```bash
docker-compose build --no-cache frontend
docker-compose up -d
```

### Database Schema Changes

1. **Create migration:**
   ```bash
   docker-compose exec tailor alembic revision --autogenerate -m "Add new field"
   ```

2. **Review migration:**
   ```bash
   cat backend/services/resume-tailor/migrations/versions/<new_file>.py
   ```

3. **Apply migration:**
   ```bash
   docker-compose exec tailor alembic upgrade head
   ```

4. **Sync to SQLite (if using hybrid mode):**
   ```bash
   docker-compose restart tailor  # Sync on boot
   ```

### Full Clean Rebuild

**Nuclear option (deletes all data):**
```bash
docker-compose down -v
docker system prune -a
docker-compose up --build
```

**Preserve data:**
```bash
# Backup first
docker-compose exec postgres pg_dump -U postgres autocareer > backup.sql
cp backend/services/resume-tailor/data/autocareer.db autocareer_backup.db

# Rebuild
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Restore if needed
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d autocareer
```

---

**Next Steps:**
- [Environment Setup](environment-setup.md) — Configure `.env` variables
- [Quickstart](quickstart.md) — Apply to your first job
- [API Reference](/docs/api/README.md) — Explore backend endpoints
