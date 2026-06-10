# Quickstart Guide

Get AutoCareer running locally in 5 minutes.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **Claude Pro/Max subscription** — install the Claude CLI and run `claude setup-token` once on your host to generate a `CLAUDE_CODE_OAUTH_TOKEN` (inference is billed against your subscription, no per-token cost)
- **Git** for cloning the repository

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/Alex-Shanyi-Yuan/job-auto-apply.git
cd job-auto-apply
```

### 2. Configure Environment Variables

Create the environment file:

```bash
cp .env.example .env
```

Edit `.env` and add your Claude credentials:

```bash
# Required - Claude via the Claude Agent SDK (default provider)
LLM_PROVIDER=claude
CLAUDE_CODE_OAUTH_TOKEN=your_oauth_token_here
# CLAUDE_MODEL=sonnet   # optional: sonnet (default) | haiku | opus

# Legacy Gemini fallback (only when LLM_PROVIDER=gemini)
# GOOGLE_API_KEY=your_gemini_api_key_here

# Database (defaults work for local development)
DATABASE_BACKEND=hybrid
SQLITE_DATABASE_URL=sqlite:///./backend/services/resume-tailor/data/autocareer.db
POSTGRES_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer

# Scraper service
SCRAPER_SERVICE_URL=http://scraper:8001
```

See [Environment Setup](./environment-setup.md) for all configuration options.

### 3. Add Your Resume

Edit your master resume content pool (structured JSON — plain text, no LaTeX needed):

```bash
nano backend/services/resume-tailor/data/master_resume.json
```

Fill in your header, education, skills, and **every** experience and project (with all bullets). The AI selects the most relevant subset per job, so be comprehensive rather than concise. See [Resume Tailoring](../features/resume-tailoring.md) for the full schema and an example.

> **Tip**: The PDF layout comes from `data/resume_template.tex.j2` (the Jake Gutierrez LaTeX template). You only edit the JSON; the LaTeX is rendered automatically.

### 4. Start All Services

Launch the full stack with Docker Compose:

```bash
docker-compose up --build
```

Wait for all services to start (approximately 1-2 minutes). You'll see:
- ✅ `frontend` listening on port 3000
- ✅ `tailor` listening on port 8000  
- ✅ `scraper` listening on port 8001
- ✅ `postgres` ready on port 5432

### 5. Open the Web UI

Visit: **http://localhost:3000**

You should see the AutoCareer dashboard.

## First Run Checklist

After opening the UI, verify the system is working:

1. **Go to Suggestions page** (`/suggestions`)
2. **Set global filter** - Example: "Software Engineer with 5+ years experience in Python"
3. **Add a job source**:
   - Name: "LinkedIn Software Jobs"
   - URL: `https://www.linkedin.com/jobs/search/?keywords=software%20engineer`
4. **Click "Refresh Suggestions"**
5. **Wait for scan to complete** (progress shown in real-time)
6. **Review suggested jobs** - You should see AI-scored jobs appear

If you see jobs with scores, the system is working! 🎉

## Stopping the Services

Press `Ctrl+C` in the terminal running `docker-compose`, then:

```bash
docker-compose down
```

To remove all data (start fresh):

```bash
docker-compose down -v
```

## Next Steps

- **[Configure job sources](../features/job-discovery.md)** - Add more job boards
- **[Understand the workflow](../architecture/data-flow.md)** - How jobs are discovered and tailored
- **[Customize your resume](../features/resume-tailoring.md)** - LaTeX customization tips
- **[Troubleshooting](./deployment.md#troubleshooting)** - Common issues and solutions

## Development Mode

For faster frontend iteration (without Docker):

```bash
# Start backend services only
docker-compose up tailor scraper postgres

# In a new terminal, run frontend locally
cd frontend
npm install
npm run dev
```

Visit: **http://localhost:3000** (frontend) talking to **http://localhost:8000** (backend)
