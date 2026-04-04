# Resume Tailoring Feature

## Overview

The Resume Tailoring feature is AutoCareer's intelligent resume customization pipeline that automatically adapts your master resume to match specific job postings. Using AI agents and LaTeX processing, it analyzes job requirements, rewrites resume content to highlight relevant experience, and generates professional PDF resumes ready for submission.

## LaTeX Workflow

AutoCareer uses **LaTeX** as the resume format for several key reasons:

1. **Professional typesetting** – Superior to Word or plain text formatting
2. **Precise control** – Consistent layout, fonts, spacing across all generated resumes
3. **Version control friendly** – Plain text files that work well with Git
4. **Programmatic manipulation** – Easy to parse, modify sections, and recompile

### Pipeline Overview

```
master.tex (your base resume)
    ↓
JobParsingAgent (extracts job requirements)
    ↓
ResumeTailorAgent (AI rewrites content to match job)
    ↓
Tailored LaTeX code
    ↓
pdflatex (compiles to PDF)
    ↓
Resume_CompanyName_JobTitle_2024-04-04_abc123.pdf
```

### Master Resume Template

**Location:** `backend/services/resume-tailor/data/master.tex`

This is your **canonical resume** – the source of truth containing:
- Complete work history
- All skills and technologies you've used
- All projects and achievements
- Education and certifications

**Key Characteristics:**
- Written in LaTeX (`.tex` file)
- Should be comprehensive, not tailored
- 1-2 pages maximum (AI will condense if needed)
- Uses standard LaTeX commands (`\section`, `\textbf`, `\itemize`, etc.)

**Example Structure:**
```latex
\documentclass[11pt,a4paper]{article}
\usepackage[utf8]{inputenc}
\usepackage{geometry}
\geometry{margin=0.75in}

\begin{document}

\section*{John Doe}
\textbf{Senior Software Engineer} \\
john.doe@email.com | (555) 123-4567 | linkedin.com/in/johndoe

\section*{Professional Summary}
Experienced software engineer with 8 years in backend development,
specializing in distributed systems, cloud infrastructure, and API design.

\section*{Skills}
\textbf{Languages:} Python, Go, TypeScript, Java \\
\textbf{Frameworks:} FastAPI, Django, React, Node.js \\
\textbf{Cloud:} AWS (EC2, S3, Lambda), GCP, Docker, Kubernetes

\section*{Experience}

\textbf{Senior Software Engineer} - TechCorp (2020 - Present)
\begin{itemize}
    \item Led migration of monolithic app to microservices, reducing latency by 40\%
    \item Designed and implemented REST API serving 10M+ requests/day
    \item Mentored 3 junior engineers on system design and best practices
\end{itemize}

\textbf{Software Engineer} - StartupXYZ (2018 - 2020)
\begin{itemize}
    \item Built real-time data processing pipeline using Python and Kafka
    \item Reduced infrastructure costs by 30\% through cloud optimization
\end{itemize}

\section*{Education}
\textbf{B.S. Computer Science} - University of Technology (2018) \\
GPA: 3.8/4.0

\end{document}
```

## Agent Roles

The tailoring pipeline uses two specialized AI agents:

### JobParsingAgent

**Purpose:** Extract structured job requirements from raw job descriptions.

**Located in:** `backend/services/resume-tailor/core/agents.py`

**What it does:**
1. Takes raw job description text (HTML cleaned to plain text)
2. Uses Google Gemini Pro to analyze the content
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
Raw job descriptions are often verbose and unstructured. The parsing agent distills them into actionable requirements that the tailoring agent can use to rewrite the resume.

### ResumeTailorAgent

**Purpose:** Rewrite the master resume to highlight relevant experience for a specific job.

**Located in:** `backend/services/resume-tailor/core/agents.py`

**What it does:**
1. Takes the master LaTeX resume and the parsed job posting
2. Analyzes which experiences, skills, and achievements align with the job requirements
3. Rewrites resume content to:
   - Emphasize relevant experience
   - Highlight matching skills
   - Tailor the professional summary to the role
   - Reorder and rephrase bullet points for maximum impact
4. Preserves **all LaTeX formatting and structure**
5. Returns a complete, valid LaTeX document ready for compilation

**Temperature:** 0.7 (allows creative rephrasing while maintaining accuracy)

**Retry Logic:** Up to 3 attempts with exponential backoff (2^n seconds) to handle transient API errors

## Prompt Engineering Details

### JobParsingAgent Prompt

**Strategy:** Extraction-focused with minimal interpretation

**Key Instructions:**
- "Extract ALL job listings visible on the page"
- "If company name is not visible, use 'Unknown Company'"
- "Return structured JSON object"

**Token Limits:**
- Job description truncated to ~8,000 characters to fit in prompt
- Focus on top of description where key requirements usually appear

### ResumeTailorAgent Prompt

**Strategy:** Expert resume writer persona with specific formatting constraints

**Key Instructions:**

1. **Writing Guidelines:**
   - "Rewrite bullet points using Google's X-Y-Z formula: 'Accomplished [X] as measured by [Y], by doing [Z]'"
   - "Highlight relevant experience and skills matching the job"
   - "Adjust professional summary to align with position"
   - "Prioritize skills mentioned in job description"
   - "Keep resume concise and impactful (strictly 1 page)"

2. **Technical Constraints:**
   - "Maintain ALL LaTeX formatting, commands, and document structure EXACTLY"
   - "Do NOT add markdown formatting - use LaTeX commands only (e.g., `\textbf{}` for bold)"
   - "Output ONLY valid LaTeX code with no additional explanations or comments"

3. **Context Provided:**
   - Full master resume LaTeX code
   - Parsed job analysis (company, title, summary, key requirements)

**Example Prompt (Abbreviated):**
```
You are an expert resume writer and LaTeX specialist with over 20 years of experience.

Your task:
- Analyze the job requirements and skills
- Rewrite the resume content to highlight relevant experience
- Tailor bullet points to emphasize achievements relevant to this role
- Rewrite bullet points using the Google formula: "Accomplished [X] as measured by [Y], by doing [Z]"
- Keep resume strictly 1 page
- Maintain ALL LaTeX formatting EXACTLY
- Output ONLY valid LaTeX code

Master Resume LaTeX:
```latex
[... full master.tex content ...]
```

Job Analysis:
Company: TechCorp
Title: Senior Backend Engineer
Summary: [...]
Key Requirements:
- 5+ years backend development
- Python and Go expertise
- Microservices architecture
[...]

Return the complete tailored LaTeX resume below:
```

**Why Temperature 0.7?**
- Lower than creative writing (0.9+) to maintain factual accuracy
- Higher than factual extraction (0.1) to allow natural rephrasing
- Balances consistency with creativity in highlighting achievements

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

## LaTeX Validation

### Pre-Compilation Checks

**Function:** `ResumeTailorAgent._validate_latex(latex_content: str) -> bool`

Before attempting to compile, the agent validates that the generated content is actually LaTeX:

**Required Patterns:**
```python
required_patterns = [
    r'\\documentclass',   # Document type declaration
    r'\\begin{document}', # Document start
    r'\\end{document}'    # Document end
]
```

If any pattern is missing → reject the output and retry (up to 3 times)

### Why This Matters

AI models sometimes:
- Wrap LaTeX in markdown code blocks (` ```latex ... ``` `)
- Add explanatory text before or after the code
- Generate incomplete documents

Validation catches these issues before wasting time on pdflatex compilation.

### Post-Compilation Validation

After pdflatex runs, check:
1. **Exit code** – 0 = success
2. **PDF file exists** – Confirms output was generated
3. **Log file** – Contains detailed error messages if compilation failed

**Common Log File Errors:**
- `! Undefined control sequence` → Unknown LaTeX command (AI hallucination)
- `! Missing $ inserted` → Math mode formatting error
- `! LaTeX Error: File 'package.sty' not found` → Missing LaTeX package

## Common Failures

### 1. Malformed LaTeX

**Symptoms:**
- pdflatex exits with non-zero code
- Log file shows syntax errors

**Causes:**
- AI generated invalid LaTeX commands
- Unescaped special characters (`&`, `%`, `$`, `#`)
- Mismatched braces `{}` or environments

**Solutions:**
- **Automatic retry:** Agent retries up to 3 times with fresh generation
- **Better prompts:** Emphasize "Output ONLY valid LaTeX code" in prompt
- **Validation:** Pre-check for common patterns before compilation

**Prevention:**
- Keep master.tex simple and well-formed (AI learns from it)
- Avoid complex custom LaTeX commands
- Use standard LaTeX packages only

### 2. Missing LaTeX Packages

**Symptoms:**
```
! LaTeX Error: File 'fancyhdr.sty' not found.
```

**Causes:**
- AI used a package not installed in the TeX distribution
- Master resume uses a rare or custom package

**Solutions:**
- **Install package:** `tlmgr install fancyhdr` (or use full TeX Live install)
- **Update master.tex:** Remove or replace the problematic package
- **Use Docker:** The `tailor` container has a comprehensive TeX Live installation

**Prevention:**
- Stick to standard packages: `geometry`, `inputenc`, `fontenc`, `hyperref`
- Test master.tex compilation before using it in AutoCareer

### 3. AI Hallucinations

**Symptoms:**
- Generated resume has fabricated achievements or skills
- Bullet points don't match actual work history
- Skills listed that aren't in master resume

**Causes:**
- AI "filling in" gaps to match job requirements
- Temperature too high (>0.8) causing creative liberties
- Insufficient context from master resume

**Solutions:**
- **Manual review:** Always check tailored resume before applying
- **Lower temperature:** Keep at 0.7 or below for factual accuracy
- **Enrich master.tex:** Include more detail so AI has real content to work with
- **Stronger prompts:** Add "Do NOT invent experience or skills not in the master resume"

**Detection:**
- Compare tailored resume side-by-side with master.tex
- Look for suspiciously perfect matches to job requirements
- Verify metrics and achievements are real

### 4. Compilation Timeout

**Symptoms:**
```
Compilation timed out after 30 seconds
```

**Causes:**
- Infinite loop in LaTeX code (rare)
- Very large document (>10 pages)
- Slow disk I/O

**Solutions:**
- **Increase timeout:** Modify `compile_latex()` timeout parameter
- **Simplify resume:** Keep to 1 page as recommended
- **Check for loops:** Look for recursive `\input` or malformed loops

### 5. Encoding Issues

**Symptoms:**
- Special characters (é, ñ, ö) render as `?` or garbage
- Compilation fails with encoding errors

**Causes:**
- Missing `\usepackage[utf8]{inputenc}` in master.tex
- Name or company has non-ASCII characters

**Solutions:**
- **Add to master.tex:**
  ```latex
  \usepackage[utf8]{inputenc}
  \usepackage[T1]{fontenc}
  ```
- **Fallback:** Use ASCII alternatives (e.g., `Resume` instead of `Résumé`)

## Customization Tips for master.tex

### 1. Document Class and Layout

**Recommended:**
```latex
\documentclass[11pt,a4paper]{article}
\usepackage{geometry}
\geometry{margin=0.75in}  % Adjust margins for conciseness
```

**Options:**
- **Font size:** 10pt (compact), 11pt (standard), 12pt (readable)
- **Paper:** `a4paper` (international), `letterpaper` (US)
- **Margins:** 0.5in (aggressive), 0.75in (balanced), 1in (spacious)

### 2. Section Formatting

**Standard Sections:**
```latex
\section*{Professional Summary}
\section*{Skills}
\section*{Experience}
\section*{Education}
\section*{Projects}  % Optional
\section*{Certifications}  % Optional
```

**Tip:** Use `\section*{}` (with asterisk) to suppress section numbering.

### 3. Bullet Points and Achievements

**Good Example (follows Google X-Y-Z formula):**
```latex
\item Reduced API latency by 40\% (from 500ms to 300ms) by implementing Redis caching layer
\item Increased test coverage from 60\% to 95\% by writing 200+ unit tests using pytest
```

**Bad Example (vague, no metrics):**
```latex
\item Worked on improving API performance
\item Wrote tests for the codebase
```

**Tailoring Agent Tip:**
The more specific and metric-driven your master.tex bullet points are, the better the AI can adapt them to different jobs.

### 4. Skills Section Organization

**Option 1: By Category**
```latex
\textbf{Languages:} Python, Go, TypeScript, Java \\
\textbf{Frameworks:} FastAPI, Django, React \\
\textbf{Tools:} Docker, Kubernetes, Git, Jenkins
```

**Option 2: By Proficiency**
```latex
\textbf{Expert:} Python, PostgreSQL, AWS \\
\textbf{Proficient:} Go, TypeScript, GCP \\
\textbf{Familiar:} Rust, Kafka, Terraform
```

**Tailoring Behavior:**
The AI will reorder and emphasize skills matching the job requirements. Include ALL skills you have—the agent will filter for relevance.

### 5. Quantifiable Metrics

**Include numbers wherever possible:**
- Team size ("Mentored 3 junior engineers")
- Scale ("Serving 10M+ requests/day")
- Performance ("Reduced costs by 30%")
- Time ("Delivered feature 2 weeks ahead of schedule")

**Why:** AI can use these metrics to craft compelling, evidence-based bullet points.

### 6. Avoiding Over-Complexity

**Keep it Simple:**
- ❌ Custom commands (`\newcommand{\myskill}[1]{...}`)
- ❌ Complex tables or multi-column layouts
- ❌ Graphics, logos, or images
- ❌ Custom fonts or exotic packages

**Rationale:** Complex LaTeX is harder for AI to preserve correctly. Stick to standard formatting.

### 7. Testing Your Master Resume

**Before using in AutoCareer:**
```bash
# Test compilation
cd backend/services/resume-tailor/data
pdflatex master.tex

# Check for errors in master.log
# Verify master.pdf looks correct
```

**Common Issues:**
- Missing `\end{document}`
- Unescaped `&` in company names
- Unclosed `\textbf{}` or `\begin{itemize}`

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

**Request to scraper service:**
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

**AI Call:** Google Gemini Pro with structured output

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

### Step 5: ResumeTailorAgent Rewrites Resume

**Input:** 
- Master LaTeX resume (read from `data/master.tex`)
- Parsed job posting

**AI Call:** Google Gemini Pro (text generation, not structured)

**Output:** Complete tailored LaTeX document

**Validation:** Check for `\documentclass`, `\begin{document}`, `\end{document}`

**Retry:** If validation fails, retry up to 2 more times

### Step 6: PDF Compilation

**LaTeXCompiler:**
1. Write tailored LaTeX to `output/resume_<uuid>.tex`
2. Run `pdflatex` (twice)
3. Check exit code and PDF existence
4. Rename to `Resume_TechCorp_Senior_Backend_Engineer_2024-04-04_<uuid>.pdf`
5. Cleanup `.aux`, `.log` files

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

### AI API Rate Limits

**Google Gemini Free Tier:**
- 15 requests per minute
- 1,500 requests per day

**Bottleneck:** Tailoring + scoring can hit rate limits with many applications

**Mitigation:**
- Add retry logic with exponential backoff (already implemented)
- Use paid tier for higher limits
- Queue applications and process slowly

### Compilation Performance

**Typical Time:**
- pdflatex (2 passes): 1-2 seconds
- AI tailoring: 5-10 seconds (depends on API latency)
- Total: ~10-15 seconds per application

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
- Check for AI API errors (rate limits, invalid API key)

### Issue: Generated resume has incorrect information

**Cause:** AI hallucination or over-creative tailoring

**Prevention:**
- Keep temperature at 0.7 or lower
- Ensure master.tex is detailed and accurate
- Add prompt constraint: "Only use information from the master resume"

**Detection:**
- Always manually review tailored resumes before sending
- Compare against master.tex for fabricated content

### Issue: PDF compilation timeout

**Cause:** Infinite loop or very large document

**Solution:**
- Simplify master.tex (remove complex commands)
- Increase timeout in `latex_compiler.py` (line 94): `timeout=60`

## Best Practices

### 1. Maintain a High-Quality Master Resume

- **Be comprehensive:** Include all relevant experience, even if old
- **Use metrics:** Quantify achievements with numbers
- **Update regularly:** Add new skills and projects as you gain them
- **Test compilation:** Ensure master.tex compiles without errors

### 2. Review Before Applying

**Always manually review tailored resumes:**
- Check for factual accuracy (no hallucinations)
- Verify formatting looks professional
- Ensure 1-page limit (or adjust if needed)
- Proofread for typos (AI can introduce errors)

### 3. Iterate on Tailoring Quality

**If results are poor:**
- Improve master.tex with more detail and metrics
- Adjust global filter to better match your background
- Experiment with prompt modifications (requires code changes)

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
- [LaTeX Compiler Implementation](../../backend/services/resume-tailor/core/latex_compiler.py) – Source code reference
