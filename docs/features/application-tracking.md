# Application Tracking Feature

## Overview

The Application Tracking feature provides a comprehensive system for managing your job application lifecycle in AutoCareer. From the moment a job is discovered as a suggestion to receiving an offer (or rejection), you can track status, view details, filter applications, and download tailored resumes—all from a centralized dashboard.

## Dashboard Usage

### Accessing the Dashboard

**URL:** `http://localhost:3000/dashboard` (or your deployed frontend URL)

**Navigation:** Click "Dashboard" in the top navigation menu

### Dashboard Layout

The dashboard displays all jobs that have progressed beyond the suggestion stage:

**Displayed Statuses:**
- `processing` – Currently generating tailored resume
- `applied` – Resume generated and ready to submit
- `interviewing` – Moved to interview stage
- `rejected` – Application rejected
- `offer` – Offer received
- `failed` – Processing failed (see error message)

**NOT Displayed:**
- `suggested` – Visible only on `/suggestions` page
- `dismissed` – User-dismissed suggestions (filtered out)

### Table Columns

| Column | Description | Example |
|--------|-------------|---------|
| **Company** | Company name (extracted from job description or URL) | "TechCorp" |
| **Title** | Job position title | "Senior Backend Engineer" |
| **Status** | Current application stage with color-coded badge | 🟡 Processing |
| **Score** | AI relevance score (0-100) with color coding | 🟢 85 |
| **Applied Date** | When the job was created/applied | "Apr 4, 2024" |
| **Actions** | Buttons for viewing details, downloading PDF, updating status | View • Download PDF • Update |

### Interactive Features

1. **Search Bar**
   - Filter by company name, job title, or keywords
   - Real-time filtering as you type
   - Case-insensitive search

2. **Status Filter Dropdown**
   - Filter by specific status (All, Applied, Interviewing, Rejected, Offer, Failed)
   - Updates table instantly
   - Shows count of matching jobs

3. **Sorting**
   - Click column headers to sort (if implemented)
   - Default: Most recent applications first (by `created_at` desc)

4. **Action Buttons**
   - **View Details:** Opens job detail page (`/jobs/[id]`)
   - **Download PDF:** Downloads tailored resume
   - **Update Status:** Dropdown to change application status

## Job Status Lifecycle

### Complete Status Flow Diagram

```
            ┌─────────────┐
            │  suggested  │ (Discovered by AI scan)
            └──────┬──────┘
                   │
         User clicks "Apply"
                   │
                   ▼
            ┌─────────────┐
            │ processing  │ (Generating tailored resume)
            └──────┬──────┘
                   │
        Success ───┼─── Failure
                   │           │
                   ▼           ▼
            ┌─────────────┐  ┌────────┐
            │   applied   │  │ failed │ (Error during tailoring)
            └──────┬──────┘  └────────┘
                   │
     User updates status manually
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
  ┌─────────┐ ┌───────┐ ┌────────┐
  │interview│ │ offer │ │rejected│
  └─────────┘ └───────┘ └────────┘

  ┌─────────────┐
  │  dismissed  │ (User action on suggestions)
  └─────────────┘
```

### Status Definitions

#### suggested
**Meaning:** AI discovered this job and scored it as potentially relevant

**Where Visible:** `/suggestions` page only (not on dashboard)

**Typical Score Range:** Any (all discovered jobs saved, even low scores)

**Next Actions:**
- **Apply:** Triggers resume tailoring (status → `processing`)
- **Dismiss:** Removes from suggestions (status → `dismissed`)

**Color:** Blue badge

---

#### processing
**Meaning:** Resume tailoring is in progress (background task running)

**Duration:** Typically 10-30 seconds

**What's Happening:**
1. Scraper fetches full job description
2. JobParsingAgent extracts requirements
3. ResumeTailorAgent rewrites resume
4. LaTeX compilation to PDF

**Next States:**
- **Success:** → `applied`
- **Failure:** → `failed` (with error message)

**Color:** Yellow badge (🟡)

**User Action:** Wait for completion (dashboard will update automatically on refresh)

---

#### applied
**Meaning:** Tailored resume successfully generated and ready for submission

**Where Visible:** Dashboard and `/jobs/[id]` detail page

**Available Actions:**
- Download PDF resume
- View full job details
- Update status to `interviewing`, `rejected`, or `offer`
- Manually mark if you submitted the application externally

**Color:** Green badge (🟢)

**Typical Workflow:**
1. Job reaches "applied" status
2. User downloads PDF
3. User submits application through company's portal
4. User manually updates status to "interviewing" if they get a response

---

#### interviewing
**Meaning:** Candidate has moved to interview stage

**Where Visible:** Dashboard, filterable by status

**User Updates Status When:**
- Received email/call for phone screen
- Scheduled for technical interview
- In any active interview process

**Next States:**
- `offer` – Received job offer
- `rejected` – Did not pass interview stage

**Color:** Blue badge (🔵)

**Tip:** Use the job detail page notes section (if implemented) to track interview rounds and feedback

---

#### rejected
**Meaning:** Application was rejected or candidate withdrew

**Where Visible:** Dashboard, filterable by status

**Common Reasons:**
- No response after application
- Explicitly rejected via email
- Failed interview process
- Candidate withdrew application

**Color:** Red badge (🔴)

**Tip:** Keep rejected applications for analytics (e.g., which types of jobs you're not getting responses for)

---

#### offer
**Meaning:** Job offer received

**Where Visible:** Dashboard, filterable by status

**User Updates When:**
- Received written or verbal offer
- Negotiation in progress
- Offer accepted or declined

**Color:** Green badge with star (🌟 or bright green)

**Tip:** Track offer details externally (salary, benefits, start date)

---

#### failed
**Meaning:** Resume tailoring or processing encountered an error

**Where Visible:** Dashboard, filterable by status

**Common Causes:**
- LaTeX compilation failure (malformed resume)
- AI API error (rate limit, timeout, invalid response)
- Scraper unable to fetch job description
- PDF generation error

**Error Message:** Stored in `error_message` field, visible on job detail page

**User Actions:**
1. View error message on job detail page
2. Check logs: `docker-compose logs -f tailor`
3. Fix underlying issue (e.g., update master.tex if LaTeX error)
4. Re-apply to job manually (if URL still valid)

**Color:** Red badge (🔴)

**Example Error Messages:**
```
"LaTeX compilation failed: ! Undefined control sequence"
"Scraper service unavailable: Connection refused"
"AI API rate limit exceeded. Retry after 60 seconds."
```

---

#### dismissed
**Meaning:** User dismissed the suggestion without applying

**Where Visible:** Nowhere (filtered out of all views)

**Purpose:** Prevents re-suggesting the same job in future scans

**Reversal:** Not currently supported (would need database update)

**API Endpoint:**
```http
POST /jobs/{id}/dismiss
```

## Score Interpretation

Every job receives an **AI-generated relevance score** from 0-100 based on how well it matches your master resume.

### Scoring Scale

| Score Range | Badge Color | Interpretation | Recommendation |
|-------------|-------------|----------------|----------------|
| **90-100** | 🟢 Dark Green | Excellent match. Nearly all requirements met. Strong background for this role. | Highly recommended to apply |
| **70-89** | 🟢 Green | Good match. Most key requirements met. Resume tailoring will highlight relevant experience well. | Recommended to apply |
| **50-69** | 🟡 Yellow | Moderate match. Some relevant skills and transferable experience. Tailoring may help but gaps exist. | Consider applying if interested |
| **30-49** | 🟠 Orange | Weak match. Significant skill gaps. Some relevant experience but may be a stretch. | Low priority, apply only if very interested |
| **0-29** | 🔴 Red | Poor match. Missing critical requirements. Application unlikely to succeed. | Not recommended unless role is aspirational |

### How Scores are Calculated

**Agent:** `JobScoringAgent` (in `core/agents.py`)

**Inputs:**
- Full job description (truncated to ~8,000 chars)
- Master resume content (truncated to ~6,000 chars)

**AI Prompt Factors:**
1. **Skills match** – Both explicit and transferable skills
2. **Experience level alignment** – Junior/Mid/Senior matching
3. **Industry/domain relevance** – Related field experience
4. **Resume tailoring potential** – Can we rewrite resume to fit this role?

**Temperature:** 0.2 (low, for consistent scoring)

**Output Schema:**
```python
class JobScore:
    score: int  # 0-100
    reasoning: str  # 2-3 sentence explanation
```

**Example Output:**
```json
{
  "score": 85,
  "reasoning": "Strong match. Candidate has 8 years of Python backend experience matching the 5+ years requirement. Microservices and cloud expertise align well with job description. Minor gap in specific framework (FastAPI vs Flask) but highly transferable."
}
```

### Score Limitations

**Important Caveats:**

1. **Non-Deterministic:** Same job re-scored may get slightly different scores (±5 points)
2. **Resume-Dependent:** Scores reflect master resume quality and completeness
3. **Not Pass/Fail:** A score of 60 doesn't mean "you won't get the job"—it means "moderate resume fit"
4. **Context-Blind:** AI doesn't know about referrals, company culture fit, or other factors
5. **Keyword-Biased:** Jobs with many buzzwords may score higher than simpler descriptions

**Best Practice:** Use scores as a **prioritization tool**, not an absolute truth. Apply to jobs you're genuinely interested in, even if score is moderate.

### Adjusting Score Thresholds

**Currently:** All discovered jobs are saved as suggestions, regardless of score

**Potential Customization (requires code change):**
Set a minimum score threshold in `server.py`:

```python
# Only save jobs with score >= 60
if job_score.score >= 60:
    save_job_as_suggestion(job)
```

**Trade-off:**
- Higher threshold = fewer low-quality suggestions
- Lower threshold = more options but noisier suggestion list

## Filtering and Search Capabilities

### Search Functionality

**Location:** Dashboard page, search bar at top

**Searchable Fields:**
- Company name
- Job title
- (Future: job URL, requirements)

**Behavior:**
- **Case-insensitive**
- **Partial matching** – "tech" matches "TechCorp", "FinTech Solutions"
- **Real-time** – Results update as you type
- **Persists on reload** – Search state saved in URL query params (if implemented)

**Example Searches:**
```
"backend"       → Matches "Backend Engineer", "Senior Backend Developer"
"TechCorp"      → Matches company name
"remote python" → Matches jobs with both keywords in title or company
```

### Status Filtering

**Location:** Dashboard page, status dropdown

**Filter Options:**
- **All** (default) – Show all jobs
- **Applied** – Only jobs with tailored resumes ready
- **Interviewing** – Active interview processes
- **Rejected** – Rejected applications
- **Offer** – Received offers
- **Failed** – Jobs with processing errors

**Behavior:**
- **Single selection** – Can only filter by one status at a time
- **Combined with search** – Search and status filter work together
- **Count display** – Shows number of jobs in each status (if implemented)

**Example Workflow:**
1. Select "Interviewing" from dropdown
2. View all active interview processes
3. Use search bar to find specific company: "Google"
4. Result: Only Google jobs in interviewing status

### Advanced Filtering (Future Enhancement)

**Potential Filters:**
- **Score range:** 70-100, 50-69, etc.
- **Date range:** Last 7 days, last 30 days, custom range
- **Source:** Filter by job board (LinkedIn, Google Jobs, etc.)
- **Has PDF:** Only jobs with successfully generated resumes

### Sorting

**Current Default:** Most recent first (by `created_at` desc)

**Potential Sort Options:**
- **Score (High to Low)** – Prioritize best matches
- **Score (Low to High)** – Review weak matches
- **Company (A-Z)** – Alphabetical by company
- **Date Applied (Newest First)** – Default behavior
- **Date Applied (Oldest First)** – Find stale applications

**Implementation:** Click column headers to toggle sort direction

## PDF Downloads

### Downloading from Dashboard

**Location:** Dashboard table, "Download PDF" button in Actions column

**Behavior:**
1. Click "Download PDF" button
2. Browser initiates download with filename: `Resume_CompanyName_JobTitle_Date_UUID.pdf`
3. PDF saved to browser's default download directory

**Requirements:**
- Job status must be `applied` (PDF successfully generated)
- PDF file must exist on server

**Error Handling:**
- If PDF not found: Display error message "PDF not available"
- If job status is `failed`: Button disabled or shows error tooltip

### Downloading from Job Detail Page

**Location:** `/jobs/[id]` page, "Download Resume" button

**Advantage:** Provides more context (job requirements, score reasoning) before downloading

### PDF Naming Convention

**Format:** `Resume_CompanyName_JobTitle_YYYY-MM-DD_UUID.pdf`

**Examples:**
```
Resume_TechCorp_Senior_Backend_Engineer_2024-04-04_a7b3c9d1.pdf
Resume_Google_Staff_Software_Engineer_2024-04-05_b2c8f3e4.pdf
Resume_Startup_XYZ_Founding_Engineer_2024-04-06_c9d1a5b7.pdf
```

**Why UUID?**
- Ensures uniqueness (can apply to same company/title multiple times)
- 8-character short UUID balances readability and collision resistance
- Allows tracking which specific resume version was sent

### Re-Downloading

**Use Case:** Lost the PDF file or need to send it again

**Process:**
1. Navigate to dashboard or job detail page
2. Click "Download PDF" button
3. Same PDF re-downloaded (not regenerated)

**Note:** The PDF is **not** regenerated when re-downloaded. If you want a newly tailored resume (e.g., master.tex was updated), you need to re-apply to the job.

### Batch Downloads (Future Feature)

**Potential Workflow:**
1. Select multiple jobs via checkboxes
2. Click "Download All PDFs" button
3. ZIP file created with all resumes
4. Single download for multiple applications

## Status Updates

### Manual Status Updates

**Location:** Dashboard table, "Update Status" dropdown in Actions column

**Available Transitions:**

From `applied`:
- → `interviewing` (received interview invitation)
- → `rejected` (no response or rejected)
- → `offer` (received offer)

From `interviewing`:
- → `offer` (interview successful)
- → `rejected` (interview unsuccessful)

From any status:
- → `applied` (reset to applied, rare)

**Workflow:**
1. Click status dropdown for a job
2. Select new status
3. Confirmation dialog (optional): "Update status to Interviewing?"
4. Status updates immediately
5. Table refreshes to reflect new status

### Automatic Status Updates

**Currently Automatic Transitions:**

- `suggested` → `processing` (when user clicks "Apply")
- `processing` → `applied` (when tailoring succeeds)
- `processing` → `failed` (when tailoring fails)

**No Automatic Transitions After `applied`:**
User must manually update status based on external events (emails, interviews, offers).

### Status Update API

**Endpoint:** (Not currently implemented, but would be:)
```http
PATCH /jobs/{id}
Content-Type: application/json

{
  "status": "interviewing"
}

Response: {
  "id": 42,
  "status": "interviewing",
  "updated_at": "2024-04-04T15:30:00"
}
```

### Status History (Future Feature)

**Potential Enhancement:**
Track all status changes with timestamps:

```json
{
  "status_history": [
    { "status": "suggested", "timestamp": "2024-04-04T10:00:00" },
    { "status": "processing", "timestamp": "2024-04-04T10:01:00" },
    { "status": "applied", "timestamp": "2024-04-04T10:01:15" },
    { "status": "interviewing", "timestamp": "2024-04-06T14:00:00" },
    { "status": "offer", "timestamp": "2024-04-10T09:00:00" }
  ]
}
```

**Use Case:** Understand time-to-hire, track application velocity

## Job Detail Page

### Accessing Job Details

**URL:** `http://localhost:3000/jobs/[id]`

**Navigation:**
- Click "View Details" button in dashboard table
- Click job card on `/suggestions` page
- Direct URL access (if you know the job ID)

### Page Sections

#### 1. Job Header
- **Company Name**
- **Job Title**
- **Status Badge** (color-coded)
- **Match Score** (with color coding)
- **Applied Date**

#### 2. Job URL
- Full URL to original job posting
- Clickable link (opens in new tab)
- Useful for checking if job is still active

#### 3. Requirements Section
**Displays:** Extracted key requirements from job description

**Format:** Bulleted list or numbered list

**Example:**
```
Key Requirements:
- 5+ years of backend development experience
- Strong proficiency in Python and Go
- Experience with microservices architecture
- Cloud platform expertise (AWS or GCP)
- Database design and optimization skills
```

**Source:** Generated by `JobParsingAgent` during application processing

#### 4. Score Reasoning
**Displays:** AI's explanation for the relevance score

**Example:**
```
Score: 85 (Good Match)

Reasoning: Strong match. Candidate has 8 years of Python backend 
experience matching the 5+ years requirement. Microservices and cloud 
expertise align well with job description. Minor gap in specific 
framework (FastAPI vs Flask) but highly transferable.
```

**Value:** Helps understand why AI scored the job this way

#### 5. Error Message (if failed)
**Displays:** Detailed error information for failed applications

**Example:**
```
Error: LaTeX compilation failed

Details: ! Undefined control sequence
Line 45: \customCommand not recognized

Suggestion: Check your master.tex for custom LaTeX commands 
and ensure all required packages are installed.
```

#### 6. Action Buttons
- **Download Resume PDF** (if status = `applied`)
- **Update Status** (dropdown to change status)
- **View on Job Board** (external link to original posting)
- **Re-apply** (if status = `failed`, retry tailoring)

## Best Practices

### 1. Regular Status Updates

**Recommended Workflow:**
- **Daily:** Review dashboard and update statuses based on emails
- **After Interviews:** Immediately update to `interviewing` to track active processes
- **After Rejections:** Mark as `rejected` to keep dashboard clean

**Why:** Accurate statuses help you:
- Prioritize follow-ups
- Avoid double-applying to same job
- Track success metrics (offer rate, time-to-hire)

### 2. Use Search and Filters Effectively

**Example Workflows:**

**Finding Active Interviews:**
1. Filter by status: "Interviewing"
2. Sort by date (oldest first)
3. Identify stale interviews that need follow-up

**Reviewing Rejections:**
1. Filter by status: "Rejected"
2. Search for company: "Tech" (finds all rejected tech companies)
3. Analyze patterns (e.g., always rejected by big tech vs. startups)

**Prioritizing Applications:**
1. Filter by status: "Applied"
2. Sort by score (high to low)
3. Focus follow-up efforts on high-match jobs

### 3. Download PDFs Immediately

**Recommendation:** Download the tailored resume PDF as soon as it's generated

**Reasons:**
- **Backup:** Protects against server data loss
- **Offline access:** Can submit application even if AutoCareer is down
- **Version control:** Keep record of exactly what resume was sent
- **Comparison:** Compare different tailored versions side-by-side

**Organization Tip:**
Create a folder structure:
```
job-applications/
  2024-04/
    Resume_TechCorp_Backend_2024-04-04.pdf
    Resume_Google_SWE_2024-04-05.pdf
  2024-05/
    ...
```

### 4. Monitor Failed Applications

**Weekly Check:**
1. Filter by status: "Failed"
2. Review error messages
3. Fix underlying issues (LaTeX errors, API limits)
4. Re-apply if still interested

**Common Fixes:**
- **LaTeX errors:** Update master.tex to remove problematic commands
- **Scraper timeouts:** Retry later or use different source URL
- **API rate limits:** Wait and retry during off-peak hours

### 5. Clean Up Old Applications

**Periodic Maintenance:**
- **Archive rejected applications** from 6+ months ago (export to CSV)
- **Delete dismissed suggestions** if database grows too large (currently kept)
- **Prune failed applications** after resolving errors

**Future Feature:** Bulk delete or archive functionality

## Analytics and Insights (Future Feature)

### Potential Metrics

**Application Funnel:**
```
Suggested: 150 jobs
Applied: 50 jobs (33% conversion)
Interviewing: 10 jobs (20% of applied)
Offers: 2 jobs (20% of interviews, 4% of applied)
```

**Average Scores by Status:**
```
Applied: Average score 75
Interviewing: Average score 82
Offers: Average score 88

Insight: Higher-scored jobs lead to more offers
```

**Time-to-Hire:**
```
Applied → Interviewing: 7 days average
Interviewing → Offer: 14 days average
Total: 21 days average
```

**Top Performing Sources:**
```
LinkedIn: 30 applied, 5 interviews (17% conversion)
Google Jobs: 15 applied, 4 interviews (27% conversion)

Insight: Google Jobs yields better interview rate
```

### Exporting Data

**Potential Export Formats:**
- **CSV:** All jobs with full details
- **JSON:** Structured data for analysis
- **PDF Report:** Summary statistics and charts

**Use Cases:**
- Import into spreadsheet for custom analysis
- Track applications across multiple job search platforms
- Share with career coach or mentor

## API Reference

### Application Tracking Endpoints

**List All Jobs (Dashboard):**
```http
GET /jobs

Response: [
  {
    "id": 1,
    "url": "https://...",
    "company": "TechCorp",
    "title": "Backend Engineer",
    "status": "applied",
    "score": 85,
    "created_at": "2024-04-04T10:30:00",
    "pdf_path": "./output/Resume_TechCorp_..."
  },
  ...
]
```

**Get Specific Job:**
```http
GET /jobs/{id}

Response: {
  "id": 42,
  "url": "https://...",
  "company": "TechCorp",
  "title": "Senior Backend Engineer",
  "status": "applied",
  "score": 85,
  "requirements": ["5+ years Python", "Microservices", ...],
  "pdf_path": "./output/Resume_TechCorp_...",
  "error_message": null,
  "created_at": "2024-04-04T10:30:00",
  "updated_at": "2024-04-04T10:31:00"
}
```

**Download Job PDF:**
```http
GET /jobs/{id}/pdf

Response: (binary PDF file)
Headers:
  Content-Type: application/pdf
  Content-Disposition: attachment; filename="Resume_TechCorp_..."
```

**Update Job Status (Future):**
```http
PATCH /jobs/{id}
Content-Type: application/json

{
  "status": "interviewing"
}

Response: {
  "id": 42,
  "status": "interviewing",
  "updated_at": "2024-04-06T14:00:00"
}
```

**Delete Job (Future):**
```http
DELETE /jobs/{id}

Response: { "message": "Job deleted successfully" }
```

## Troubleshooting

### Issue: Job not appearing on dashboard

**Possible Causes:**
1. Status is `suggested` or `dismissed` (only shown on `/suggestions`)
2. Browser cache is stale (hard refresh: Ctrl+Shift+R or Cmd+Shift+R)
3. Backend service is down

**Solution:**
1. Check job status via API: `GET /jobs/{id}`
2. Verify backend is running: `docker-compose ps`
3. Check browser console for errors (F12 → Console tab)

### Issue: PDF download fails

**Error:** "PDF not available" or 404 error

**Causes:**
1. PDF file deleted or moved on server
2. Job status is not `applied` (tailoring failed or still in progress)
3. PDF path in database is incorrect

**Solution:**
1. Check job detail page for error message
2. Verify job status is `applied`
3. Check server logs: `docker-compose logs tailor | grep "PDF"`
4. Re-apply to job to regenerate PDF (if URL still valid)

### Issue: Status update doesn't persist

**Symptom:** Change status dropdown, but it reverts on page refresh

**Causes:**
1. Frontend not calling update API
2. Database write failed
3. Browser cache showing stale data

**Solution:**
1. Open browser dev tools (F12) → Network tab
2. Update status and check for PATCH request
3. If no request: Frontend bug (check console for errors)
4. If request fails: Check backend logs for database errors

### Issue: Search/filter not working

**Symptom:** Typing in search bar or changing filter has no effect

**Causes:**
1. JavaScript error in frontend
2. State management issue (React state not updating)

**Solution:**
1. Check browser console (F12) for errors
2. Hard refresh page (Ctrl+Shift+R)
3. Clear browser cache and cookies
4. Report issue with console error logs

## Related Documentation

- [Job Discovery](./job-discovery.md) – How jobs get into the system
- [Resume Tailoring](./resume-tailoring.md) – What happens when you click "Apply"
- [Frontend API Client](../../frontend/lib/api.ts) – TypeScript API reference
