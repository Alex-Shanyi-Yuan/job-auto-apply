# Quick Start Guide - AutoCareer

Get up and running in 5 minutes!

## Prerequisites

- Docker and Docker Compose installed
- Google Gemini API key

## Setup Steps

### 1. Get Your Gemini API Key

1. Visit https://makersuite.google.com/app/apikey
2. Sign in and click "Create API Key"
3. Copy the generated key

### 2. Configure Environment

```bash
cd backend/services/resume-tailor
cp .env.example .env
```

Edit `.env` and add your API key:
```
GOOGLE_API_KEY=AIzaSyC...your_actual_key_here
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autocareer
SCRAPER_SERVICE_URL=http://scraper:8001
```

### 3. Prepare Your Resume

Edit `data/master.tex` with your actual resume content. The provided template is just an example.

### 4. Start All Services

From the project root:
```bash
cd /path/to/job-auto-apply
docker-compose up --build
```

This takes 2-3 minutes on first run (downloads Python + TeX Live + Playwright).

### 5. Open the Web UI

Navigate to: **http://localhost:3000**

## Using the Web UI

### Step 1: Set Up Global Filter

1. Go to **Suggestions** page
2. Find the **Global Filter** card (purple)
3. Click **Edit** and enter your job preferences:
   ```
   Software Engineer roles, 3-5 years experience, 
   Python or JavaScript, remote-friendly
   ```
4. Click **Save**

### Step 2: Add Job Sources

1. In the **Job Sources** section, click **Add Source**
2. Enter:
   - **Name**: e.g., "LinkedIn Python Jobs"
   - **URL**: A job board search results URL
   - **Filter** (optional): Source-specific criteria
3. Click **Add Source**

Example URLs:
- LinkedIn: `https://www.linkedin.com/jobs/search/?keywords=python%20developer`
- Indeed: `https://www.indeed.com/jobs?q=software+engineer`

### Step 3: Discover Jobs

1. Click **Refresh Suggestions**
2. Watch the progress panel:
   - Sources being scanned
   - Jobs found and scored
3. Wait for completion

### Step 4: Review & Apply

For each suggested job:
- **Score** (0-100): Higher = better match
- **Apply**: Generate tailored resume
- **Dismiss**: Remove from suggestions

### Step 5: Track Applications

Go to **Dashboard** to:
- See all applied jobs
- Check status (Processing → Applied)
- Download tailored PDFs

## Common Issues

**"Connection refused"**
- Make sure `docker-compose up` is running
- Wait for all services to start (check logs)

**"GOOGLE_API_KEY not found"**
- Make sure you edited `.env` (not `.env.example`)
- Restart services: `docker-compose restart tailor`

**"No jobs found"**
- Check if the source URL returns search results in a browser
- Some sites block automated requests
- Try a different job board

**PDF download fails**
- Check the job status on Dashboard
- Look for error messages
- Check tailor service logs: `docker-compose logs tailor`

## Next Steps

- Add more job sources for broader coverage
- Refine your global filter for better matches
- Keep your master resume comprehensive and up-to-date
- Review tailored resumes before submitting applications

## Help

- [Full Documentation](README.md)
- [API Specification](spec.md)
- [Project Architecture](../../../README.md)
