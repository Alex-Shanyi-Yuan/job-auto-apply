# Project Specification: Job Application Automation SaaS ("AutoCareer")

## 1. Executive Summary

**AutoCareer** is a SaaS platform designed to automate the job search and application process for high-value candidates. The system aggregates high-paying job postings, filters them based on user-defined criteria and experience compatibility, uses Large Language Models (LLMs) to tailor application assets (resumes, cover letters), and facilitates the application process.

### Core Value Proposition

* **High-Signal Sourcing:** Only surfacing jobs that meet strict salary/tier criteria
* **Intelligent Filtering:** Using LLMs to discard jobs where the user is under/over-qualified
* **Hyper-Personalization:** Rewriting resumes for every single application
* **Application Tracking:** Centralized dashboard for all applied roles

## 2. System Architecture (Hybrid: Next.js + Python Serverless)

We will use a **Hybrid Architecture** where Next.js acts as the orchestrator and Python Lambdas act as specialized workers.

### The "Orchestrator" (Frontend & API)

**Framework:** Next.js 14+ (App Router)  
**Hosting:** Vercel or AWS Amplify

**Responsibility:**
* User Authentication (Auth.js / Clerk)
* Database Operations (CRUD on Users/Jobs)
* Stripe Payments
* Orchestration: Deciding when to call the Python workers

### The "Workers" (Compute Layer)

**Runtime:** AWS Lambda (Python 3.11)

**Responsibility:**
* **Resume Parser:** Extracting text from PDFs
* **The Tailor:** Running heavy LLM prompts (LangChain/OpenAI)
* **PDF Compiler:** Running `pdflatex` to generate final assets

---

## 2a. Alternative: Local Development Architecture (Self-Hosted)

For users who prefer to run everything locally (or on a VPS) without AWS Cloud dependencies, the system can be run entirely via **Docker Compose**.

### The "Orchestrator" (Local)
* **Runtime:** Node.js (Next.js) running on `localhost:3000`
* **Database:** PostgreSQL (running in Docker) instead of DynamoDB

### The "Workers" (Local)
* **Runtime:** Python API Server (FastAPI) running in Docker
* **Exposure:** Exposed on `localhost:8000`
* **Storage:** Local Docker Volumes (instead of S3)

**Benefits of Local Approach:**
* Zero cloud costs during development
* Faster feedback loop (no deployment time)
* Full control over data privacy

---

## 3. Detailed Module Specifications

### Module A: Job Ingestion & Sourcing Engine (Next.js Cron)

**Runtime:** Next.js API Route (Cron Job) or simple Lambda

**Data Sources:**
* Aggregator APIs: Integrate with Theirstack or JSearch

**Process:**
1. Fetch jobs from API (TypeScript)
2. Check DynamoDB for duplicates
3. Save new jobs to DB

**Note:** TypeScript is perfect here because it's just JSON shuffling.

### Module B: The Intelligent Filter (Python Lambda)

**Runtime:** Python Lambda

**Why Python?** Complex text analysis and "fuzzy matching" are easier with Python libraries.

**Trigger:** EventBridge event when new jobs are added  
**Input:** User Profile JSON + Job Description Text  
**Output:** `{ "match_score": 85, "reason": "..." }`

### Module C: Resume Tailoring Engine (Python Lambda)

**Runtime:** Python Lambda (Container Image)

**Why Container?** We need to bundle a full LaTeX distribution (approx 500MB), which is too large for a standard Lambda zip.

**Process:**
1. **Input:** Master Resume (LaTeX) + Job Description
2. **LLM Task:** Rewrite specific LaTeX sections
3. **Compilation:** Run `pdflatex` subprocess to build PDF
4. **Storage:** Upload result to S3
5. **Response:** Return the S3 Signed URL to Next.js

### Module D: The Application Agent (Browser Extension)

**Runtime:** Client-Side JavaScript (Plasmo Framework)

**Process:**
1. User clicks "Apply" on a job board (e.g., Workday)
2. Extension fetches the tailored resume data from Next.js API
3. Extension auto-fills the DOM elements on the page

## 4. Data Model (Hybrid Database Strategy)

We use a hybrid database approach to leverage the strengths of both SQL and NoSQL.

### Primary Database: PostgreSQL (Job Data & Filtering)

Since the core functionality involves complex filtering of job postings (e.g., "Salary > $150k AND Remote AND Python"), we use **PostgreSQL** for storing job data.

**Table: Jobs**
* `id` (UUID, PK)
* `title` (Text)
* `company` (Text)
* `salary_min` (Int)
* `salary_max` (Int)
* `is_remote` (Boolean)
* `tech_stack` (Array/JSONB)
* `description` (Text)
* `created_at` (Timestamp)

**Why Postgres?**
* Efficient complex queries (`WHERE salary > X AND remote = true`)
* Full text search for job descriptions
* Easy local hosting via Docker

### Secondary Database: DynamoDB (User Session & State)

For simple key-value lookups and high-scale user state, we can optionally use DynamoDB (or just use Postgres for everything in the local version).

**Table: Users**
* **PK:** `USER#{userId}`
* **Attributes:** `email`, `stripe_customer_id`, `credits_remaining`

**Table: Applications**
* **PK:** `USER#{userId}`
* **SK:** `APP#{jobHash}`
* **Attributes:** `status`, `s3_url`, `match_score`

---

## 4a. Database Strategy: DynamoDB vs. PostgreSQL

While the initial design uses DynamoDB (for AWS Serverless synergy), **PostgreSQL is strongly recommended** for the Local/Self-Hosted version.

### Why PostgreSQL?

1.  **Complex Filtering:** The core feature of this app is filtering jobs (e.g., "Show me jobs > $150k AND Remote AND Python").
    *   **DynamoDB:** Requires expensive "Scans" or complex GSI management for multi-field filtering.
    *   **PostgreSQL:** Simple `WHERE salary > 150000 AND remote = true` queries.
2.  **Relational Data:** The app has clear relationships: `Users` -> `Applications` -> `Jobs`. SQL handles joins naturally.
3.  **Local Development:** Running a Postgres container is standard and lightweight compared to mocking DynamoDB.

### How to Host PostgreSQL Locally?
Simply add a service to your `docker-compose.yml`:

```yaml
services:
  db:
    image: postgres:15-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: autocareer
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

This allows the Next.js app to connect via `DATABASE_URL="postgresql://user:password@localhost:5432/autocareer"`.

---

## 5. Interface Contract (TypeScript <-> Python)

To prevent errors, we define **Shared Interfaces** in TypeScript that match the Python output.

**TypeScript Interface:**

```typescript
interface TailorResponse {
  jobId: string;
  s3Url: string; // The result PDF
  generatedCoverLetter: string;
  tokenUsage: number;
}
```

**Next.js Call (Example):**

```typescript
// Next.js Server Action
async function generateApplication(jobId: string) {
  const result = await fetch(process.env.PYTHON_LAMBDA_URL, {
    method: 'POST',
    body: JSON.stringify({ jobId, userId: currentUser.id })
  });
  return result.json() as TailorResponse;
}
```

## 6. Development Phases

### Phase 1: Local Hybrid Dev

* **Backend:** Run the Python script (`main.py`) locally on port 8000 (FastAPI or simple script)
* **Frontend:** Run Next.js on port 3000
* **Connection:** Next.js proxies requests to `localhost:8000`

### Phase 2: Cloud Deployment

* **Backend:** Deploy Python code to AWS Lambda (using SST or Serverless Framework)
* **Frontend:** Deploy Next.js to Vercel/Amplify
* **Connection:** Next.js calls the private Lambda Function URL

## 7. Recommended Tech Stack Summary

| Component | Technology | Reasoning |
|-----------|-----------|-----------|
| Orchestrator | Next.js (App Router) | Best-in-class for UI, Auth, and simple API routes |
| Worker Runtime | AWS Lambda (Python) | Access to powerful AI/NLP libraries and LaTeX tools |
| Infrastructure | SST (Ion) | Define both Next.js and Python Lambdas in one `sst.config.ts` |
| Database | DynamoDB | Single-digit millisecond latency for job tracking |
| LLM | OpenAI GPT-4o | Via `openai` Python SDK |
| PDF Engine | LaTeX (TeX Live) | Bundled in a Docker container for Lambda |
