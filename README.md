# Project Specification: Job Application Automation SaaS ("AutoCareer")

## 1. Executive Summary

**AutoCareer** is a self-hosted SaaS platform designed to automate the job search and application process. It aggregates job postings, filters them based on user-defined criteria, uses Large Language Models (LLMs) to tailor application assets (resumes), and tracks the application process via a centralized dashboard.

### Core Value Proposition

* **Automated Tailoring:** Rewriting resumes for every single application using Google Gemini Pro.
* **Application Tracking:** Centralized dashboard for all applied roles.
* **Privacy-First:** Self-hosted architecture ensures your data stays on your machine.

## 2. System Architecture (Microservices)

We use a **Microservices Architecture** orchestrated by Docker Compose.

### The "Orchestrator" (Frontend)

**Framework:** Next.js 14 (App Router)
**UI Library:** shadcn/ui + Tailwind CSS
**Port:** `3000`

**Responsibility:**
* User Interface for Dashboard and Job Details.
* Triggering backend processes via API calls.
* Displaying real-time status updates.

### The "Workers" (Backend Services)

#### Service A: Resume Tailor Service
**Runtime:** Python 3.11 (FastAPI)
**Port:** `8000`
**Responsibility:**
* **API Server:** Handles requests from Frontend.
* **Orchestration:** Calls Scraper Service, then invokes LLM Agents.
* **Resume Tailoring:** Uses Gemini Pro to rewrite resume sections.
* **PDF Compilation:** Uses `pdflatex` to generate final PDFs.
* **Database Management:** CRUD operations on PostgreSQL.

#### Service B: Job Scraper Service
**Runtime:** Python 3.11 (FastAPI) + Playwright
**Port:** `8001`
**Responsibility:**
* **Headless Browsing:** Renders dynamic JavaScript content.
* **Extraction:** Returns clean text from job URLs.

### The "Persistence" (Database)

**System:** PostgreSQL 15
**Port:** `5432`
**Responsibility:**
* Storing Job Applications, Status, and Metadata.
* Data persistence via Docker Volumes.

---

## 3. Detailed Module Specifications

### Module A: Job Scraper Service

**Technology:** Playwright + BeautifulSoup + FastAPI

**Process:**
1. Receives `POST /scrape` with URL.
2. Launches headless Chromium browser.
3. Renders page and extracts raw HTML.
4. Cleans HTML to text using BeautifulSoup.
5. Returns structured JSON `{ title, text, url }`.

### Module B: Resume Tailor Service

**Technology:** FastAPI + SQLModel + Google Gemini + LaTeX

**Process:**
1. **Ingest:** Receives `POST /apply` from Frontend.
2. **Scrape:** Calls Module A to get job text.
3. **Parse:** Uses LLM to extract "Key Requirements" from job text.
4. **Tailor:** Uses LLM to rewrite Master Resume based on requirements.
5. **Compile:** Generates PDF from tailored LaTeX.
6. **Save:** Updates Database with status and PDF path.

### Module C: Frontend Dashboard

**Technology:** Next.js + React Query (or `useEffect` polling)

**Process:**
1. **Dashboard:** Lists all jobs with status badges (Applied, Processing, Failed).
2. **Job Details:** Shows job metadata, key requirements, and PDF download.
3. **Polling:** Periodically checks backend for status updates.

---

## 4. Data Model (PostgreSQL)

**Table: `job`**

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `Integer` (PK) | Unique ID |
| `url` | `String` | Original Job URL |
| `company` | `String` | Company Name |
| `title` | `String` | Job Title |
| `status` | `String` | `processing`, `applied`, `failed` |
| `requirements` | `JSON` | List of key requirements extracted by AI |
| `pdf_path` | `String` | Path to generated PDF |
| `created_at` | `DateTime` | Timestamp |

---

## 5. Development Workflow

### Prerequisites
* Docker & Docker Compose
* Google Gemini API Key

### Running the Stack
```bash
docker-compose up --build
```

### Access Points
* **Frontend:** http://localhost:3000
* **Tailor API:** http://localhost:8000/docs
* **Scraper API:** http://localhost:8001/docs
* **Database:** localhost:5432 (User: `user`, Pass: `password`, DB: `autocareer`)
