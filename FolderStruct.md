# AutoCareer Project Structure

This structure follows a **Monorepo pattern**. It allows you to develop the frontend and backend side-by-side.

## Top-Level Directory

```
/autocareer-monorepo
├── .gitignore
├── package.json               # Root scripts (e.g., "dev": "concurrently 'npm run dev:web' 'npm run dev:api'")
├── README.md
├── sst.config.ts              # Infrastructure as Code (defines AWS Lambda & Next.js linkage)
├── .env.local                 # Global Environment Variables (OpenAI Keys, AWS Secrets)
│
├── /frontend                  # The "Orchestrator" (Next.js)
│   └── ... (See Section 1)
│
└── /backend                   # The "Workers" (Python)
    └── ... (See Section 2)
```

## 1. Frontend Structure (Next.js)

Located in `/frontend`. This handles the UI, Auth, and orchestrating calls to the Python backend.

```
/frontend
├── package.json
├── next.config.js
├── tsconfig.json
│
├── /app                       # Next.js App Router
│   ├── layout.tsx             # Root layout (Auth providers wrap here)
│   ├── page.tsx               # Landing page
│   │
│   ├── /dashboard             # User Dashboard (Protected)
│   │   ├── page.tsx
│   │   └── /jobs              # Job Tracking View
│   │
│   └── /api                   # Next.js API Routes
│       ├── /webhooks          # Stripe Webhooks
│       └── /cron              # Module A: Job Sourcing (Runs nightly)
│           └── route.ts
│
├── /components                # React UI Components
│   ├── /ui                    # Shadcn/Tailwind primitives (Buttons, Cards)
│   └── /features              # Complex components (ResumeUploader, JobCard)
│
├── /lib                       # Shared Logic
│   ├── db.ts                  # DynamoDB Client (DocumentClient)
│   ├── api-client.ts          # Typed fetcher for calling Python Backend
│   └── types.ts               # Shared Interfaces (match Python output)
│
└── /public                    # Static assets
```

## 2. Backend Structure (Python Microservices)

Located in `/backend`. Split by "Service" to allow different deployment strategies (e.g., Docker for Resume Tailor, Zip for Filter).

```
/backend
│
├── /services
│   │
│   ├── /resume-tailor         # Module C: The Heavy Lifter
│   │   ├── Dockerfile         # CRITICAL: Installs Python 3.11 + TeX Live (LaTeX)
│   │   ├── requirements.txt   # openai, boto3, fastapi, uvicorn
│   │   ├── main.py            # Local Dev Server (FastAPI)
│   │   │
│   │   ├── /core              # Business Logic
│   │   │   ├── parser.py      # Module 1 (Reads .tex)
│   │   │   ├── llm.py         # Module 2 (OpenAI/LangChain)
│   │   │   └── compiler.py    # Module 3 (Subprocess pdflatex)
│   │   │
│   │   └── /templates         # LaTeX Master Templates
│   │       └── master.tex
│   │
│   └── /job-filter            # Module B: Lightweight AI Filter
│       ├── requirements.txt   # lighter deps (no latex)
│       └── handler.py         # Pure Lambda function
│
└── /scripts                   # Utilities
    └── seed_jobs.py           # Script to populate DynamoDB with dummy jobs
```

## 3. Workflow Explanation

### Local Development (Phase 1)

You will run two terminals (or one `concurrently` command):

**Terminal A (Frontend):** Runs `next dev` on `localhost:3000`.

**Terminal B (Backend):** Runs `python backend/services/resume-tailor/main.py` (FastAPI) on `localhost:8000`.

**Connection:** In `.env.local`, set `PYTHON_API_URL="http://localhost:8000"`.

The Next.js API Client sends requests to localhost.

### Cloud Deployment (Phase 2 - SST)

When you deploy using SST (`npx sst deploy`):

* **Frontend:** SST deploys the Next.js app to AWS (via OpenNext or Amplify)
* **Backend:** SST builds the Docker image for `resume-tailor`, pushes it to ECR, and creates a Lambda Function URL
* **Connection:** SST automatically injects the real Lambda URL into the Next.js environment variables
