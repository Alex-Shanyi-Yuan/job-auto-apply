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
GOOGLE_API_KEY=your_gemini_api_key_here
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

Get your Gemini API key from: https://makersuite.google.com/app/apikey

## API Overview

### Job Discovery & Suggestions

| Endpoint               | Method     | Description              |
| ---------------------- | ---------- | ------------------------ |
| `/sources`             | GET/POST   | Manage job board sources |
| `/sources/{id}`        | PUT/DELETE | Update/delete sources    |
| `/suggestions`         | GET        | List AI-discovered jobs  |
| `/suggestions/refresh` | POST       | Trigger new job scan     |
| `/suggestions/status`  | GET        | Get scan progress        |

### Resume Tailoring

| Endpoint             | Method | Description            |
| -------------------- | ------ | ---------------------- |
| `/apply`             | POST   | Start resume tailoring |
| `/jobs`              | GET    | List all applied jobs  |
| `/jobs/{id}`         | GET    | Get job details        |
| `/jobs/{id}/pdf`     | GET    | Download tailored PDF  |
| `/jobs/{id}/dismiss` | POST   | Dismiss a suggestion   |

### Settings

| Endpoint                  | Method  | Description          |
| ------------------------- | ------- | -------------------- |
| `/settings/global-filter` | GET/PUT | Global filter prompt |

See [spec.md](spec.md) for complete API documentation.

## AI Agents

The service uses four specialized AI agents:

| Agent               | Purpose                                       |
| ------------------- | --------------------------------------------- |
| `JobDiscoveryAgent` | Extracts job listings from search result HTML |
| `JobScoringAgent`   | Scores job-resume match (0-100)               |
| `JobParsingAgent`   | Extracts requirements from job descriptions   |
| `ResumeTailorAgent` | Rewrites resume sections for each job         |

## Project Structure

```
resume-tailor/
├── core/                      # Core modules
│   ├── agents.py             # AI Agents (Discovery, Scoring, Parsing, Tailoring)
│   ├── jd_scraper.py         # Job description fetching
│   ├── llm_client.py         # Gemini API integration
│   ├── models.py             # Data models
│   └── latex_compiler.py     # PDF compilation
├── migrations/               # Alembic database migrations
│   └── versions/
├── data/
│   └── master.tex            # Your master resume template
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
| `GOOGLE_API_KEY`        | Gemini API key                                            | Required                                              |
| `DATABASE_BACKEND`      | Active backend (`postgres`, `sqlite`, `hybrid`)           | `postgres`                                            |
| `SQLITE_DATABASE_URL`   | SQLite connection string                                  | `sqlite:///./data/autocareer.db`                      |
| `POSTGRES_DATABASE_URL` | PostgreSQL connection string                              | `postgresql://user:password@postgres:5432/autocareer` |
| `DB_SYNC_ENABLED`       | Enable Postgres/SQLite reconcile                          | `true`                                                |
| `SYNC_ON_BOOT`          | Reconcile at startup when Postgres is reachable           | `true`                                                |
| `SYNC_ON_SHUTDOWN`      | Reconcile at graceful shutdown when Postgres is reachable | `true`                                                |
| `SCRAPER_SERVICE_URL`   | Scraper service URL                                       | `http://scraper:8001`                                 |
| `MASTER_RESUME_PATH`    | Path to LaTeX template                                    | `./data/master.tex`                                   |

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

### "GOOGLE_API_KEY not found"

Make sure you created `.env` (not `.env.example`) with your actual key.

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
