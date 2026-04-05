# AutoCareer - AI-Powered Job Application Automation

A self-hosted platform that uses AI to discover jobs, score them by relevance, and automatically tailor your resume for each application.

## ✨ Key Features

- 🔍 **AI Job Discovery** - Automatically find relevant jobs from configured sources
- 📊 **Smart Scoring** - AI-powered relevance scoring (0-100) based on your resume  
- 🤖 **Resume Tailoring** - Automatically customize your resume for each job
- 📋 **Application Tracking** - Centralized dashboard for all applications
- 📡 **Live Pipeline Progress** - Real-time SSE updates while resumes are being tailored
- 🛡️ **Startup Health & Quality Gates** - Fail-fast startup checks and hook-based validation

## 🚀 Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/Alex-Shanyi-Yuan/job-auto-apply.git
cd job-auto-apply

# 2. Configure environment
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY

# 3. Add your resume
nano backend/services/resume-tailor/data/master.tex

# 4. Start all services
docker-compose up --build
docker compose --profile postgres up --build # if using postgresql


# 5. Open the web UI
# Visit: http://localhost:3000
```

## 📚 Documentation

See **[docs/](./docs/)** for complete documentation:

- **[Quickstart Guide](./docs/getting-started/quickstart.md)** - Detailed setup instructions
- **[Architecture](./docs/architecture/overview.md)** - How the system works
- **[Features](./docs/features/)** - Job discovery, resume tailoring, tracking
- **[API Reference](./docs/api/)** - Backend API endpoints

## 🛠️ Technology Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- **Backend**: Python 3.11, FastAPI, SQLModel
- **AI**: Google Gemini Pro
- **Database**: PostgreSQL / SQLite (hybrid mode supported)
- **PDF**: TeX Live (pdflatex)

## 🔒 Privacy First

Self-hosted architecture - your data never leaves your machine.

## 📝 License

MIT

---

**Need help?** Check the [documentation](./docs/) or open an issue.
