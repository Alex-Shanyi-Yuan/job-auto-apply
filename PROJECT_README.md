# AutoCareer - Job Application Automation

A self-hosted platform for automating job search and application processes using AI.

## Features

- 🔍 **AI Job Discovery** - Automatically find relevant jobs from configured sources
- 📊 **Smart Scoring** - AI-powered relevance scoring (0-100) based on your resume
- 🤖 **Resume Tailoring** - Automatically customize your resume for each job
- 📋 **Application Tracking** - Centralized dashboard for all applications
- 🔒 **Privacy-First** - Self-hosted, your data stays on your machine

## Project Structure

```
/job-auto-apply
├── frontend/          # Next.js web application
├── backend/           # Python microservices
├── docker-compose.yml # Service orchestration
└── README.md          # System architecture
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key ([Get one here](https://makersuite.google.com/app/apikey))

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/Alex-Shanyi-Yuan/job-auto-apply.git
   cd job-auto-apply
   ```

2. **Set up environment variables**
   ```bash
   cd backend/services/resume-tailor
   cp .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Add your master resume**
   - Edit `backend/services/resume-tailor/data/master.tex` with your resume

4. **Start all services**
   ```bash
   cd /path/to/job-auto-apply
   docker-compose up --build
   ```

5. **Open the web UI**
   ```
   http://localhost:3000
   ```

## Usage

### 1. Configure Job Sources

Go to **Suggestions** → **Add Source**:
- Add job board search URLs (LinkedIn, Indeed, etc.)
- Set a global filter (e.g., "Software Engineer, 5+ years experience")
- Optionally add source-specific filters

### 2. Discover Jobs

Click **Refresh Suggestions** to:
- Scan all configured sources
- AI extracts job listings from search results
- AI scores each job (0-100) based on your resume

### 3. Apply to Jobs

For each suggested job:
- Review the AI score and job details
- Click **Apply** to generate a tailored resume
- Or **Dismiss** to remove from suggestions

### 4. Track Applications

Go to **Dashboard** to:
- View all applied jobs
- Check application status
- Download tailored PDFs

## Architecture

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 3000 | Next.js web UI |
| Tailor API | 8000 | Python FastAPI backend |
| Scraper | 8001 | Playwright headless browser |
| PostgreSQL | 5432 | Database |

## Technology Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python 3.11, FastAPI, SQLModel, Alembic
- **AI**: Google Gemini Pro
- **Database**: PostgreSQL 15
- **PDF**: TeX Live (pdflatex)
- **Scraping**: Playwright, BeautifulSoup

## Development

### Run services separately

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

**Backend:**
```bash
cd backend/services/resume-tailor
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
```

### Database migrations

```bash
cd backend/services/resume-tailor
alembic upgrade head
```

## Documentation

- [System Architecture](./README.md) - Detailed system design
- [Folder Structure](./FolderStruct.md) - Project organization
- [API Specification](./backend/services/resume-tailor/spec.md) - All endpoints
- [Resume Tailor](./backend/services/resume-tailor/README.md) - Backend service docs

## License

MIT
