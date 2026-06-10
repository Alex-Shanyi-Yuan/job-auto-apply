# Resume Tailoring Feature

## Overview

The Resume Tailoring feature is AutoCareer's intelligent resume customization pipeline that automatically adapts your master resume to match specific job postings. The master resume lives as **structured JSON data** (a pool of every experience, project, and skill). For each job, an AI agent selects and rewords the most relevant subset, and a deterministic renderer turns the result into a compilable LaTeX document and a professional PDF.

## Structured Content Pipeline

The LLM **never writes LaTeX**. It only produces validated, structured data (`ResumeContent`); a fixed Jinja2 template renders that data to LaTeX with every value escaped. This eliminates the unbalanced-brace / unescaped-character failure class of the old "ask the LLM for a LaTeX document" approach, and guarantees ATS-parsable output.

### Pipeline Overview

```
master_resume.json (your full content pool)
    ↓  load_master_resume_content() → ResumeContent (Pydantic-validated)
JobParsingAgent (extracts job requirements → JobPosting)
    ↓
ResumeTailorAgent (AI selects + rewords the most relevant subset → ResumeContent)
    ↓  _enforce_budget() (hard one-page caps, header restored verbatim)
render_resume() (Jinja2 template + LaTeX escaping → always-compilable LaTeX)
    ↓
pdflatex (compiles to PDF)
    ↓
Resume_CompanyName_JobTitle_2024-04-04_abc123.pdf
```

### Key Files

| File | Role |
| --- | --- |
| `backend/services/resume-tailor/data/master_resume.json` | **Source of truth.** Your full content pool: header, education, skills, summary, every experience and project with all bullets. |
| `backend/services/resume-tailor/core/resume_model.py` | Pydantic models (`ResumeContent`, `ExperienceEntry`, `ProjectEntry`, …) with field constraints (no empty strings, bounded lengths). |
| `backend/services/resume-tailor/core/resume_renderer.py` | `render_resume(content) -> str` — deterministic LaTeX rendering with escaping. |
| `backend/services/resume-tailor/data/resume_template.tex.j2` | Jinja2 LaTeX template (Jake Gutierrez resume layout). |
| `backend/services/resume-tailor/data/master.tex` | Legacy LaTeX resume, kept as the visual reference for the template. Not used by the tailoring pipeline (the startup `master_resume_presence` check still looks for it via `MASTER_RESUME_PATH`). |

### The Master Resume Pool (`master_resume.json`)

**Location:** `backend/services/resume-tailor/data/master_resume.json` (configurable via `MASTER_RESUME_JSON_PATH`)

This is your **canonical resume content** – comprehensive, not tailored:

- Complete work history (one entry per company; multiple roles per company supported)
- All skills, grouped by category
- All projects with tech tags and bullets
- Education and header (name, phone, email, links, citizenship)

**Example structure:**

```json
{
  "header": {
    "name": "John Doe",
    "phone": "(555) 123-4567",
    "email": "john.doe@email.com",
    "links": [
      { "label": "linkedin.com/in/johndoe", "url": "https://linkedin.com/in/johndoe" },
      { "label": "github.com/johndoe", "url": "https://github.com/johndoe" }
    ],
    "citizenship": "US Citizen"
  },
  "education": [
    {
      "institution": "University of Technology",
      "location": "City, ST",
      "degree": "B.S. Computer Science",
      "dates": "2014 -- 2018",
      "highlights": ["GPA: 3.8/4.0"]
    }
  ],
  "skills": [
    { "category": "Languages", "items": ["Python", "Go", "TypeScript"] },
    { "category": "Frameworks", "items": ["FastAPI", "React"] }
  ],
  "summary": "Experienced software engineer ...",
  "experience": [
    {
      "company": "TechCorp",
      "location": "Remote",
      "roles": [
        { "title": "Senior Software Engineer", "dates": "2020 -- Present" },
        { "title": "Software Engineer", "dates": "2018 -- 2020" }
      ],
      "bullets": [
        "Led migration of monolithic app to microservices, reducing latency by 40%",
        "Designed and implemented REST API serving 10M+ requests/day"
      ]
    }
  ],
  "projects": [
    {
      "name": "AutoCareer",
      "tech": ["Python", "FastAPI", "Next.js"],
      "bullets": ["Built a self-hosted job application automation platform"],
      "link": "https://github.com/johndoe/autocareer"
    }
  ]
}
```

**Validation:** the file is parsed into `ResumeContent` at load time. Empty bullets, missing required fields, or over-long entries are rejected with a clear Pydantic error (bullets ≤ 400 chars, skill items ≤ 80 chars, etc.). Plain text only — no LaTeX commands needed; special characters (`&`, `%`, `#`, …) are escaped automatically at render time.

## Agent Roles

The tailoring pipeline uses two specialized AI agents:

### JobParsingAgent

**Purpose:** Extract structured job requirements from raw job descriptions.

**Located in:** `backend/services/resume-tailor/core/agents.py`

**What it does:**
1. Takes raw job description text (HTML cleaned to plain text)
2. Uses Claude via the `claude-agent-sdk` (default engine; Gemini is a legacy fallback) to analyze the content
3. Extracts key information into a structured `JobPosting` object:
   - Company name
   - Job title
   - Role summary (2-3 sentences)
   - List of key requirements (skills, experience, qualifications)

**Output Schema (Pydantic):**
```python
class JobPosting:
    company_name: str
    job_title: str
    summary: str
    key_requirements: List[str]
    raw_text: str  # Original job description for reference
```

**Example Output:**
```json
{
  "company_name": "TechCorp",
  "job_title": "Senior Backend Engineer",
  "summary": "TechCorp is seeking an experienced backend engineer to design and build scalable APIs for our cloud platform. The role involves leading architectural decisions and mentoring junior developers.",
  "key_requirements": [
    "5+ years of backend development experience",
    "Strong proficiency in Python and Go",
    "Experience with microservices architecture",
    "Cloud platform expertise (AWS or GCP)",
    "Database design and optimization skills",
    "Leadership and mentoring abilities"
  ]
}
```

**Why This Matters:**
Raw job descriptions are often verbose and unstructured. The parsing agent distills them into actionable requirements that the tailoring agent can use to select and reword resume content.

### ResumeTailorAgent

**Purpose:** Select and reword the most relevant content from the master pool for a specific job.

**Located in:** `backend/services/resume-tailor/core/agents.py`

**What it does:**
1. Receives the **full master pool** (`ResumeContent` as JSON) and the parsed `JobPosting`
2. Asks the LLM (structured output, `generate_structured` with the `ResumeContent` schema) to:
   - **Select** the most relevant experiences/projects and drop the rest
   - **Order** them by relevance to the job
   - **Reword** bullets to mirror the job's keywords (truthfully, X-Y-Z style)
   - Reorder skills to surface job-relevant ones first
   - Never fabricate experience, employers, skills, or metrics
3. Applies `_enforce_budget()` — deterministic guardrails after the LLM:
   - Header restored **verbatim** from the master (the model can never alter contact details)
   - Hard one-page caps: `MAX_EXPERIENCE=5`, `MAX_PROJECTS=5`, `MAX_BULLETS_PER_EXPERIENCE=5`, `MAX_BULLETS_PER_PROJECT=3`, `MAX_SKILL_GROUPS=5`
   - Falls back to the full master content if the model returns an empty selection

**Output:** a validated `ResumeContent` — never LaTeX.

**Retry Logic:** the apply pipeline retries a failed tailoring step up to `MAX_RETRIES` (default 3, env-configurable) with the job's `retry_count` tracked in the database.

## Prompt Engineering Details

### JobParsingAgent Prompt

**Strategy:** Extraction-focused with minimal interpretation

**Key Instructions:**
- "If company name is not explicitly stated, infer from context or use 'Unknown Company'"
- "Return the result as a structured JSON object matching the schema"

**Token Limits:**
- Job description truncated to fit in prompt
- Focus on top of description where key requirements usually appear

### ResumeTailorAgent Prompt

**Strategy:** Expert resume writer persona, optimizing for ATS keyword match — selection and rewording of structured data, never formatting.

**Key Instructions (from `agents.py`):**

1. **Selection & ordering:**
   - "SELECT the most relevant experiences and projects for this job and DROP the least relevant"
   - "ORDER experiences and projects by relevance to the job (most relevant first)"
   - "Target a single page"

2. **Rewording:**
   - "REWRITE bullet points to mirror the job's key requirements and terminology wherever it is truthful, keeping them quantified and in the 'Accomplished X as measured by Y, by doing Z' style"
   - "Reorder and trim the skills to surface the most job-relevant ones first"

3. **Safety constraints:**
   - "Keep the header EXACTLY as given" (also enforced in code afterwards)
   - "NEVER fabricate experience, employers, skills, or metrics"
   - "Plain text only in every field — no markdown and no LaTeX commands"

4. **Context provided:** the parsed job (company, title, summary, key requirements) and the full master pool as JSON (`master.model_dump_json()`).

The structured-output schema (`ResumeContent`) is enforced by the LLM provider, so a malformed response fails validation loudly instead of producing a broken document.

## Deterministic LaTeX Rendering

**Located in:** `backend/services/resume-tailor/core/resume_renderer.py`

`render_resume(content)` renders the tailored `ResumeContent` through a fixed Jinja2 template:

- **Template:** `data/resume_template.tex.j2` — the Jake Gutierrez resume layout, with section blocks for header, education, skills, summary, experience, and projects. Empty sections are omitted automatically.
- **LaTeX-safe delimiters:** Jinja2 is configured with `<< … >>` for variables and `<% … %>` for blocks so the template never clashes with LaTeX braces.
- **Escaping:** every interpolated value passes through the `tex` filter (`latex_escape`), which escapes all 10 LaTeX special characters (`\ & % $ # _ { } ~ ^`) in a single pass. URLs pass through `texurl`, which escapes only `%` and `#` so `\href` links stay valid.
- **StrictUndefined:** a typo in the template fails loudly instead of rendering an empty value.

Because the structure comes from the template and all content is escaped, **the output is always compilable** — there is no "validate the LLM's LaTeX" step anymore.

## PDF Generation Process

### LaTeXCompiler Class

**Located in:** `backend/services/resume-tailor/core/latex_compiler.py`

**Workflow:**

1. **Write `.tex` file** to disk (`output/` directory)
   - Unique filename with UUID to avoid collisions
   - UTF-8 encoding to support special characters

2. **Run `pdflatex` command** (2 passes for references)
   ```bash
   pdflatex -interaction=nonstopmode \
            -output-directory=./output \
            resume_abc123.tex
   ```

3. **Check for compilation errors**
   - Exit code 0 = success
   - Non-zero = failure (check `.log` file)

4. **Rename PDF with descriptive name**
   - Format: `Resume_CompanyName_JobTitle_YYYY-MM-DD_UUID.pdf`
   - Sanitizes company/title (alphanumeric + underscores)
   - Truncates title to 30 characters
   - Adds short UUID (8 chars) for uniqueness

5. **Cleanup auxiliary files**
   - Removes `.aux`, `.log`, `.out`, `.toc`, etc.
   - Optionally removes intermediate `.tex` file

**Example Output:**
```
Resume_TechCorp_Senior_Backend_Engineer_2024-04-04_a7b3c9d1.pdf
```

### pdflatex Requirements

**The `pdflatex` binary must be installed** for PDF compilation to work:

- **Linux:** `apt-get install texlive-latex-base texlive-latex-extra`
- **macOS:** Install MacTeX (`brew install --cask mactex`)
- **Windows:** Install MiKTeX
- **Docker (Recommended):** Use the `tailor` service container which has TeX Live pre-installed

**Verification:**
```bash
pdflatex --version
# Should output: pdfTeX 3.x (TeX Live 2023)
```

### Compilation Parameters

- **`-interaction=nonstopmode`** – Don't pause on errors (needed for automation)
- **`-output-directory`** – Write all files to a specific directory
- **2 compilation passes** – Resolves cross-references and labels (standard LaTeX practice)
- **30-second timeout** – Prevents infinite loops in malformed LaTeX

## Common Failures

### 1. Invalid Structured Output from the LLM

**Symptoms:**
- Tailoring step fails with a Pydantic validation error
- `RETRY_ATTEMPT` events in the job's SSE stream

**Causes:**
- LLM returned JSON that violates the `ResumeContent` schema (empty bullets, missing fields)

**Solutions:**
- **Automatic retry:** the apply pipeline retries the tailoring step up to `MAX_RETRIES` times
- Schema validation happens at the provider layer, so a bad response never reaches rendering

> Note: malformed *LaTeX* is no longer a failure mode for generated content — the template is fixed and all values are escaped. If pdflatex fails, the bug is in `resume_template.tex.j2` itself, not in the LLM output.

### 2. Missing LaTeX Packages

**Symptoms:**
```
! LaTeX Error: File 'fancyhdr.sty' not found.
```

**Causes:**
- The template uses a package not installed in the TeX distribution (the stock template needs `fullpage`, `titlesec`, `marvosym`, `enumitem`, `hyperref`, `fancyhdr`, `babel`, `tabularx`)

**Solutions:**
- **Install package:** `tlmgr install fancyhdr` (or use full TeX Live install)
- **Use Docker:** The `tailor` container has a comprehensive TeX Live installation

### 3. AI Hallucinations

**Symptoms:**
- Generated resume has fabricated achievements or skills
- Bullet points don't match actual work history

**Causes:**
- AI "filling in" gaps to match job requirements

**Mitigations already in place:**
- Prompt rule: "NEVER fabricate experience, employers, skills, or metrics. Only reuse and rephrase what is in the pool."
- The header (name/contact) is restored verbatim in code after tailoring
- The model can only select/reword from the pool you wrote in `master_resume.json`

**Detection:**
- Always manually review tailored resumes before applying
- Compare bullets side-by-side with `master_resume.json`
- Verify metrics and achievements are real

### 4. Compilation Timeout

**Symptoms:**
```
Compilation timed out after 30 seconds
```

**Causes:**
- Very slow disk I/O, or a template bug introducing an infinite loop (rare)

**Solutions:**
- **Increase timeout:** Modify `compile_latex()` timeout parameter
- **Check the template** if you've customized `resume_template.tex.j2`

### 5. Encoding Issues

**Symptoms:**
- Special characters (é, ñ, ö) render as `?` or garbage

**Causes:**
- Non-ASCII characters in `master_resume.json` that the template's font setup can't render

**Solutions:**
- The template uses `\pdfgentounicode=1` for ATS-parsable output; most accented Latin characters work
- **Fallback:** Use ASCII alternatives (e.g., `Resume` instead of `Résumé`)

## Maintaining Your Master Resume Pool

### 1. Be Comprehensive — the AI Filters for You

Include **everything** in `master_resume.json`: every job, project, and skill. The tailoring agent selects the most relevant subset per job and the budget guardrails keep the result to one page. More pool content = better tailoring.

### 2. Bullet Points and Achievements

**Good (follows the X-Y-Z formula):**
```json
"Reduced API latency by 40% (from 500ms to 300ms) by implementing a Redis caching layer"
```

**Bad (vague, no metrics):**
```json
"Worked on improving API performance"
```

The more specific and metric-driven your bullets are, the better the AI can adapt them to different jobs.

### 3. Plain Text Only

Write bullets as plain text. Do **not** embed LaTeX commands (`\textbf{}`, etc.) — special characters are escaped automatically, so embedded commands would render literally.

### 4. Multiple Roles per Company

Use the `roles` list to show a promotion or contract-to-hire under one company heading:

```json
"roles": [
  { "title": "Senior Software Engineer", "dates": "2022 -- Present" },
  { "title": "Software Engineer", "dates": "2020 -- 2022" }
]
```

### 5. Customizing the Layout

Layout changes (fonts, margins, section order) go in `data/resume_template.tex.j2`, not in the JSON. Keep template edits small and run the renderer tests (`tests/test_resume_renderer.py`) after changing it. Remember the Jinja2 delimiters are `<< >>` / `<% %>`.

### 6. Validating Your Pool

```bash
cd backend/services/resume-tailor
TESTING=true /path/to/repo/.venv/bin/python -c "
from server import load_master_resume_content
from core.resume_renderer import render_resume
content = load_master_resume_content('./data/master_resume.json')
print(render_resume(content)[:500])
"
```

A Pydantic error here means the JSON violates the schema (empty strings, over-long bullets, missing required fields).

## Full Tailoring Workflow Example

### Step 1: User Clicks "Apply" on a Job

**Frontend:** `/suggestions` page → user clicks "Apply" button on a job card

**API Call:**
```http
POST /apply
Content-Type: application/json

{
  "url": "https://techcorp.com/jobs/backend-engineer-12345"
}
```

### Step 2: Background Processing Begins

**Backend:** `server.py` → `process_application()` function runs as background task

**Status:** Job status set to `"processing"`

### Step 3: Scraper Fetches Job Description

**Request to scraper service** (via `scrape_url()`, which retries timeouts/5xx with exponential backoff):
```http
POST http://scraper:8001/scrape
Content-Type: application/json

{
  "url": "https://techcorp.com/jobs/backend-engineer-12345",
  "format": "text"
}
```

**Returns:** Cleaned plain text of job description

### Step 4: JobParsingAgent Extracts Requirements

**Input:** Raw job description text

**AI Call:** Claude via `claude-agent-sdk` with structured output (Gemini fallback if `LLM_PROVIDER=gemini`)

**Output:**
```python
JobPosting(
    company_name="TechCorp",
    job_title="Senior Backend Engineer",
    summary="TechCorp is seeking...",
    key_requirements=[
        "5+ years Python/Go experience",
        "Microservices architecture",
        ...
    ]
)
```

### Step 5: ResumeTailorAgent Selects and Rewords Content

**Input:**
- Master content pool (`ResumeContent` loaded from `data/master_resume.json`)
- Parsed job posting

**AI Call:** Claude via `claude-agent-sdk` with structured output against the `ResumeContent` schema (Gemini fallback if `LLM_PROVIDER=gemini`)

**Output:** Tailored `ResumeContent` (subset of the pool, reworded, ordered by relevance)

**Guardrails:** `_enforce_budget()` restores the header verbatim and caps experiences/projects/bullets for a one-page result

**Retry:** On failure, the pipeline retries up to `MAX_RETRIES` times (tracked on the job record, surfaced as SSE `RETRY_ATTEMPT` events)

### Step 6: Rendering + PDF Compilation

1. `render_resume(tailored_content)` → complete LaTeX document (deterministic, escaped)
2. **LaTeXCompiler:** write `output/resume_<uuid>.tex`, run `pdflatex` (twice), check exit code and PDF existence
3. Rename to `Resume_TechCorp_Senior_Backend_Engineer_2024-04-04_<uuid>.pdf`
4. Cleanup `.aux`, `.log` files

**Output Path:** `backend/services/resume-tailor/output/Resume_TechCorp_...pdf`

### Step 7: Database Update

**Save Job Record:**
```python
Job(
    url="https://techcorp.com/jobs/backend-engineer-12345",
    company="TechCorp",
    title="Senior Backend Engineer",
    status="applied",
    requirements=json.dumps(key_requirements),
    pdf_path="./output/Resume_TechCorp_...",
    created_at=datetime.now()
)
```

**Status:** `"applied"` (success) or `"failed"` (if any step errored)

### Step 8: User Downloads PDF

**Frontend:** Navigate to `/dashboard`, click "Download PDF" button

**API Call:**
```http
GET /jobs/42/pdf
```

**Response:** PDF file with headers:
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="Resume_TechCorp_Senior_Backend_Engineer_2024-04-04_abc123.pdf"
```

## Performance Optimization

### Caching Considerations

**Currently:** No caching (each application generates a fresh tailored resume)

**Potential Optimizations:**
1. **Cache parsed job descriptions** – If same URL applied multiple times
2. **Cache master resume** – Load once at startup, not per application
3. **Parallel applications** – Tailor multiple jobs simultaneously

### AI Inference Limits

**Claude (default engine):**
- Inference runs through the `claude-agent-sdk`, billed against your Claude Pro/Max subscription (authenticated via `CLAUDE_CODE_OAUTH_TOKEN`) — no per-token API cost.
- Calls go through the `claude` CLI subprocess (~3–13s each), so latency is higher than the old Gemini HTTP path.

**Gemini (legacy fallback, `LLM_PROVIDER=gemini`):** subject to Google's per-token API rate limits and billing.

**Bottleneck:** Tailoring + scoring throughput is bounded by per-call latency, and the Gemini fallback can hit Google's rate limits with many applications.

**Mitigation:**
- Add retry logic with exponential backoff (already implemented)
- Queue applications and process slowly

### Compilation Performance

**Typical Time:**
- pdflatex (2 passes): 1-2 seconds
- AI tailoring (default Claude engine via `claude` CLI subprocess): ~3-13 seconds per call
- Total: varies with LLM latency per application

**Optimization:**
- Run pdflatex only once if no cross-references needed
- Use faster LaTeX engine (e.g., LuaTeX) for complex documents

## API Reference

### Tailoring Endpoint

**Trigger Resume Tailoring:**
```http
POST /apply
Content-Type: application/json

{
  "url": "https://company.com/careers/job-123"
}

Response: {
  "id": 42,
  "status": "processing",
  "message": "Application started in background"
}
```

**Get Job Details (includes PDF path):**
```http
GET /jobs/42

Response: {
  "id": 42,
  "url": "https://company.com/careers/job-123",
  "company": "TechCorp",
  "title": "Senior Backend Engineer",
  "status": "applied",
  "requirements": ["5+ years Python", "Microservices", ...],
  "pdf_path": "./output/Resume_TechCorp_...",
  "score": 85,
  "created_at": "2024-04-04T10:30:00",
  "error_message": null
}
```

**Download PDF:**
```http
GET /jobs/42/pdf

Response: (binary PDF file)
```

### Error Responses

**Job Not Found:**
```http
GET /jobs/999

Status: 404
Response: { "detail": "Job not found" }
```

**Compilation Failed:**
```http
GET /jobs/42

Status: 200
Response: {
  "id": 42,
  "status": "failed",
  "error_message": "LaTeX compilation failed: ! Undefined control sequence",
  ...
}
```

## Troubleshooting Guide

### Issue: "pdflatex not found in system PATH"

**Cause:** TeX Live not installed or not in PATH

**Solution:**
```bash
# Install TeX Live (Linux)
sudo apt-get install texlive-latex-base texlive-latex-extra

# Or use Docker
docker-compose exec tailor pdflatex --version
```

### Issue: Job status stuck in "processing"

**Cause:** Background task crashed or is still running

**Diagnosis:**
```bash
# Check Docker logs
docker-compose logs -f tailor

# Look for errors in the process_application function
```

**Solution:**
- Restart the tailor service: `docker-compose restart tailor`
- Check for LLM errors (Claude auth/timeout, or Gemini rate limits when using the fallback)

### Issue: Generated resume has incorrect information

**Cause:** AI hallucination or over-creative rewording

**Prevention:**
- Ensure `master_resume.json` is detailed and accurate — the model can only select from it
- The header is restored from the master in code, so contact details are always correct

**Detection:**
- Always manually review tailored resumes before sending
- Compare against `master_resume.json` for fabricated content

### Issue: Pydantic validation error when loading the master resume

**Cause:** `master_resume.json` violates the `ResumeContent` schema

**Solution:**
- Read the error message — it names the exact field (e.g., empty bullet, bullet over 400 chars, missing `roles`)
- See `core/resume_model.py` for all field constraints

## Best Practices

### 1. Maintain a High-Quality Master Pool

- **Be comprehensive:** Include all relevant experience, even if old — selection happens per job
- **Use metrics:** Quantify achievements with numbers
- **Update regularly:** Add new skills and projects as you gain them
- **Validate:** Loading the JSON catches schema errors immediately

### 2. Review Before Applying

**Always manually review tailored resumes:**
- Check for factual accuracy (no hallucinations)
- Verify formatting looks professional
- Proofread for typos (AI can introduce errors)

### 3. Iterate on Tailoring Quality

**If results are poor:**
- Improve `master_resume.json` with more detail and metrics
- Adjust global filter to better match your background
- Experiment with prompt modifications in `core/agents.py` (requires code changes)

### 4. Organize Output PDFs

**File naming convention is designed for easy sorting:**
```
Resume_Company_Title_Date_UUID.pdf
```

**Tips:**
- Keep a backup folder of all generated resumes
- Track which resume was sent to which company
- Use the date to identify version (if reapplying)

## Related Documentation

- [Job Discovery](./job-discovery.md) – How jobs are found and scored
- [Application Tracking](./application-tracking.md) – Managing application status
- [Resume Model](../../backend/services/resume-tailor/core/resume_model.py) – `ResumeContent` schema source
- [Resume Renderer](../../backend/services/resume-tailor/core/resume_renderer.py) – Deterministic LaTeX rendering
- [LaTeX Compiler Implementation](../../backend/services/resume-tailor/core/latex_compiler.py) – Source code reference
