# Quick Start Guide - Resume Tailor

Get up and running in 5 minutes!

## Prerequisites

- Docker installed (or Python 3.11+ with TeX Live)
- Google Gemini API key

## Setup Steps

### 1. Get Your Gemini API Key

1. Visit https://makersuite.google.com/app/apikey
2. Sign in and click "Create API Key"
3. Copy the generated key

### 2. Configure Environment

```bash
cd backend/services/resume-tailor
copy .env.example .env
```

Edit `.env` and replace `your_gemini_api_key_here` with your actual key:
```
GOOGLE_API_KEY=AIzaSyC...your_actual_key_here
```

### 3. Prepare Your Resume

Edit `data/master.tex` with your actual resume content. The provided template is just an example.

### 4. Build Docker Container

```bash
docker-compose build
```

This takes 2-3 minutes (downloads Python + TeX Live).

### 5. Run Your First Tailoring

Save a job description to a text file:

**job_description.txt**
```
Senior Software Engineer

TechCorp is looking for a talented backend engineer...

Requirements:
- 5+ years Python experience
- AWS and Docker expertise
- Strong system design skills
```

Then run:
```bash
docker-compose run tailor --file job_description.txt
```

You should see:
```
============================================================
                    Resume Tailor CLI                      
============================================================

📄 Loading master resume...
   ✓ Loaded 4321 characters from ./data/master.tex

🔍 Fetching job description...
   Source: job_description.txt
   ✓ Retrieved 543 characters

🤖 Tailoring resume with Gemini Pro...
   (This may take 10-30 seconds...)
   ✓ Received tailored resume (4198 characters)

📄 Compiling LaTeX to PDF...
✓ LaTeX file written to: output/tailored_resume.tex
Compiling to PDF...
✓ PDF compiled successfully
✓ PDF saved as: output/Resume_TechCorp_2024-12-04.pdf
✓ Auxiliary files cleaned up

============================================================
                        🎉 Success!                        
============================================================

Resume saved to: D:\job-auto-apply\backend\services\resume-tailor\output\Resume_TechCorp_2024-12-04.pdf
```

### 6. Check Your Output

Open `output/Resume_TechCorp_2024-12-04.pdf` to see your tailored resume!

## Next Steps

### Tailor from URL
```bash
docker-compose run tailor --url "https://www.linkedin.com/jobs/view/12345"
```

### Use Custom Output Name
```bash
docker-compose run tailor --file job.txt --output "Google_L4_SWE"
```

### Run Without Docker (if you have TeX Live installed)
```bash
python main.py --file job_description.txt
```

## Common Issues

**"pdflatex not found"**
- You're probably running `python main.py` instead of `docker-compose run tailor`
- Docker includes TeX Live automatically

**"GOOGLE_API_KEY not found"**
- Make sure you edited `.env` (not `.env.example`)
- No quotes needed around the API key

**"Failed to fetch URL"**
- Some job sites block scrapers
- Save the job description manually and use `--file` instead

## Tips

- Always review the generated resume before submitting
- Keep your master resume comprehensive and up-to-date
- Use specific company names with `--output` for better organization
- The tool preserves your original `master.tex` - it's never modified

## Help

Run with `--help` to see all options:
```bash
docker-compose run tailor --help
```

Or check the full [README.md](README.md) for detailed documentation.
