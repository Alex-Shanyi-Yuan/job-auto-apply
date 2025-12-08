# Local Resume Tailor: Module Specifications (LaTeX Edition - Python)

## Goal
A local CLI tool that takes a Master LaTeX Resume (.tex) and a Job Description, sends both to Google Gemini Pro, and compiles the tailored output into a PDF.

## 1. System Context

### Architecture
**Dockerized Python 3.11+** environment with bundled TeX Live distribution.

### Prerequisites
* Docker installed (handles all dependencies)
* OR Manual setup: Python 3.11+ and TeX Live locally

### Storage
* `./backend/services/resume-tailor/data/master.tex`: Your source resume
* `./backend/services/resume-tailor/output/`: Generated PDFs and .tex files

### Configuration
`.env` file in `backend/services/resume-tailor/` with `GOOGLE_API_KEY` for Gemini Pro.

## Module 1: Job Description Scraper

**Responsibility:** Fetch job description content from a URL or read from a text file, and parse it into structured data.

**Location:** `backend/services/resume-tailor/core/jd_scraper.py`

**Input:** URL string or file path to text file.

**Processing:**
* If URL: Use `requests` to fetch HTML
* Use `BeautifulSoup` to extract text content (strip tags, scripts, styles)
* If file: Read directly with `open()`
* Clean excessive whitespace and normalize line breaks
* **Parsing:** Use `JobParsingAgent` (from `agents.py`) to extract structured info (Company, Role, Requirements) into a `JobPosting` model.

**Output:** `JobPosting` object (Pydantic model).

**Dependencies:** `requests`, `beautifulsoup4`, `pydantic`

---

## Module 2: LLM Client & Agents

**Responsibility:** Handle interactions with Google Gemini Pro. `GeminiClient` provides the low-level API wrapper, while `ResumeTailorAgent` handles the specific prompting logic.

**Location:** 
* `backend/services/resume-tailor/core/llm_client.py` (Generic Client)
* `backend/services/resume-tailor/core/agents.py` (Business Logic)
* `backend/services/resume-tailor/core/models.py` (Data Structures)

**Input:**
* `master_latex`: Complete contents of `master.tex` as string
* `job_posting`: Structured `JobPosting` object

**Prompt Strategy (in `ResumeTailorAgent`):**
```
You are an expert resume writer and LaTeX specialist. 

I will provide you with:
1. A complete LaTeX resume file
2. A job description

Your task:
- Analyze the job description and identify key requirements, skills, and qualifications
- Rewrite the resume content to highlight relevant experience and skills
- Tailor bullet points to emphasize achievements that match the job requirements
- Adjust the professional summary to align with the role
- Maintain ALL LaTeX formatting, commands, and document structure
- Output ONLY valid LaTeX code, no markdown or explanations

Master Resume LaTeX:
{master_latex}

Job Description:
{job_description_text}

Return the complete tailored LaTeX resume:
```

**Processing:**
* `GeminiClient`: Initializes `google.genai` client with `GOOGLE_API_KEY`.
* `ResumeTailorAgent`: Constructs the prompt and calls `GeminiClient`.
* Validates response contains LaTeX document structure.

**Output:** Tailored LaTeX document as string.

**Dependencies:** `google-genai`, `pydantic`

---

## Module 3: LaTeX Compiler

**Responsibility:** Write the tailored LaTeX to a file and compile it to PDF using system's TeX distribution.

**Location:** `backend/services/resume-tailor/core/latex_compiler.py`

**Input:**
* `tailored_latex`: Complete LaTeX document string from Gemini
* `output_filename`: Desired PDF filename (e.g., "Resume_CompanyName_2024-12-04")

**Processing:**
1. **File Write:** Save `tailored_latex` to `./output/tailored_resume.tex`
2. **Compilation:** Execute `pdflatex` via `subprocess.run()`:
   ```python
   subprocess.run([
       "pdflatex",
       "-interaction=nonstopmode",
       "-output-directory=./output",
       "./output/tailored_resume.tex"
   ], check=True)
   ```
3. **Multiple Passes:** Run `pdflatex` twice (required for references, TOC, etc.)
4. **Cleanup:** Remove auxiliary files (`.aux`, `.log`, `.out`)
5. **Rename:** Move `tailored_resume.pdf` to final filename

**Error Handling:**
* If `pdflatex` not found: Print error message with installation instructions
* If compilation fails: Save the `.tex` file and `.log` for debugging
* Return status and path to generated PDF

**Output:** Path to compiled PDF file.

**Dependencies:** System must have `pdflatex` in PATH (provided by TeX Live in Docker)

---

## Module 4: CLI Orchestrator

**Responsibility:** Command-line interface that coordinates the entire workflow.

**Location:** `backend/services/resume-tailor/main.py`

**Command Syntax:**
```bash
python main.py --url "https://jobs.example.com/posting"
python main.py --file "job_description.txt"
python main.py --text "Job Title: Senior Engineer..."
```

**Arguments:**
* `--url`: URL to fetch job description from
* `--file`: Path to text file containing job description
* `--text`: Inline job description text
* `--output`: (Optional) Custom output filename prefix

**Workflow:**
1. **Parse Arguments:** Use `argparse` to handle CLI inputs
2. **Load Master Resume:** Read `./data/master.tex`
3. **Fetch Job Description:** 
   - If `--url`: Call `jd_scraper.fetch_from_url()`
   - If `--file`: Call `jd_scraper.read_from_file()`
   - If `--text`: Use directly
4. **Tailor Resume:** Call `llm_client.tailor_resume(master_latex, job_description)`
5. **Compile PDF:** Call `latex_compiler.compile_pdf(tailored_latex, output_filename)`
6. **Display Result:** Print success message with PDF path

**Output Example:**
```
🚀 Fetching job description from URL...
✅ Job description retrieved (1,234 characters)

🤖 Sending to Gemini Pro for tailoring...
✅ Received tailored resume (3,456 characters)

📄 Compiling LaTeX to PDF...
✅ PDF compiled successfully

🎉 Success! Resume saved to:
   ./output/Resume_TechCorp_2024-12-04.pdf
```

---

## Directory Structure (Updated for Existing Project)

```
/job-auto-apply
  /backend
    /services
      /resume-tailor
        ├── Dockerfile                    # Python 3.11 + TeX Live
        ├── docker-compose.yml            # Easy local development
        ├── requirements.txt              # Python dependencies
        ├── .env.example                  # Template for API keys
        ├── .env                          # Your actual keys (gitignored)
        ├── main.py                       # CLI entry point (Module 4)
        │
        ├── /core                         # Business logic modules
        │   ├── __init__.py
        │   ├── jd_scraper.py            # Module 1
        │   ├── llm_client.py            # Module 2 (Client)
        │   ├── agents.py                # Module 2 (Logic)
        │   ├── models.py                # Data Models
        │   └── latex_compiler.py        # Module 3
        │
        ├── /data
        │   └── master.tex               # Your source resume
        │
        └── /output                       # Generated files
            ├── tailored_resume.tex
            ├── tailored_resume.pdf
            └── Resume_*.pdf
```

---

## Docker Setup

**Dockerfile:**
* Base: `python:3.11-slim`
* Install TeX Live (`texlive-latex-base`, `texlive-fonts-recommended`)
* Copy requirements and install Python packages
* Set working directory to `/app`

**docker-compose.yml:**
* Mount local `data/` and `output/` directories as volumes
* Pass environment variables from `.env` file
* Easy commands: `docker-compose run tailor --url "https://..."`

**Benefits:**
* No need to install TeX Live on host machine
* Consistent environment across different systems
* Easy to deploy to cloud later

---

## Dependencies (requirements.txt)

```
requests>=2.31.0
beautifulsoup4>=4.12.0
google-genai
python-dotenv>=1.0.0
pydantic>=2.0.0
```

---

## Environment Variables (.env)

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## Usage Examples

### Using Docker (Recommended)
```bash
# Build the container
docker-compose build

# Run with URL
docker-compose run tailor --url "https://www.linkedin.com/jobs/view/12345"

# Run with local file
docker-compose run tailor --file "./data/job_description.txt"
```

### Using Local Python
```bash
# Install dependencies
pip install -r requirements.txt

# Run the tool
python main.py --url "https://jobs.example.com/posting"
```

---

## Future Enhancements (Out of Scope for v1)

* Support for multiple resume templates
* Web UI for non-technical users
* Integration with job board APIs
* Batch processing multiple jobs
* A/B testing different tailoring strategies

