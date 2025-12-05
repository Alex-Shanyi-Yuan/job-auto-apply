# Resume Tailor - LaTeX Resume Automation with Gemini Pro

A CLI tool that automatically tailors your LaTeX resume to match specific job descriptions using Google's Gemini Pro AI.

## Features

- 🤖 **AI-Powered Tailoring**: Uses Google Gemini Pro to intelligently adapt your resume
- 📄 **LaTeX Support**: Works with your existing LaTeX resume templates
- 🌐 **Flexible Input**: Fetch job descriptions from URLs, files, or direct text
- 🐳 **Dockerized**: Includes all dependencies (Python + TeX Live) in one container
- 📊 **Smart Extraction**: Automatically detects company names for file naming
- 🎯 **Focused Output**: Generates clean PDFs with automatic cleanup of auxiliary files

## Quick Start

### Option 1: Using Docker (Recommended)

1. **Build the container**
   ```bash
   cd backend/services/resume-tailor
   docker-compose build
   ```

2. **Set up your API key**
   ```bash
   copy .env.example .env
   # Edit .env and add your GOOGLE_API_KEY
   ```

3. **Add your master resume**
   - Place your LaTeX resume at `data/master.tex`
   - Or edit the provided sample template

4. **Run the tool**
   ```bash
   # From a URL
   docker-compose run tailor --url "https://jobs.example.com/posting"
   
   # From a file
   docker-compose run tailor --file "job_description.txt"
   
   # With custom output name
   docker-compose run tailor --url "https://..." --output "GoogleSRE"
   ```

### Option 2: Local Installation

1. **Prerequisites**
   - Python 3.11+
   - TeX Live (or MacTeX/MiKTeX) installed with `pdflatex` in PATH

2. **Install dependencies**
   ```bash
   cd backend/services/resume-tailor
   pip install -r requirements.txt
   ```

3. **Configure**
   ```bash
   copy .env.example .env
   # Edit .env with your GOOGLE_API_KEY
   ```

4. **Run**
   ```bash
   python main.py --url "https://jobs.example.com/posting"
   ```

## Usage Examples

### Basic Usage
```bash
# Tailor resume from job URL
python main.py --url "https://www.linkedin.com/jobs/view/12345"

# Use local job description file
python main.py --file "job_posting.txt"

# Direct text input
python main.py --text "Software Engineer at TechCorp. Requirements: Python, AWS..."
```

### Advanced Options
```bash
# Custom output filename
python main.py --url "https://..." --output "Meta_E5_Backend"

# Use different master resume
python main.py --url "https://..." --master "./data/resume_ml.tex"

# Keep auxiliary LaTeX files for debugging
python main.py --url "https://..." --no-cleanup

# Custom output directory
python main.py --url "https://..." --output-dir "./custom_output"
```

## Project Structure

```
resume-tailor/
├── core/                      # Core modules
│   ├── __init__.py
│   ├── jd_scraper.py         # Job description fetching
│   ├── llm_client.py         # Gemini API integration
│   └── latex_compiler.py     # PDF compilation
├── data/
│   └── master.tex            # Your master resume (edit this!)
├── output/                    # Generated PDFs and .tex files
├── main.py                    # CLI entry point
├── requirements.txt           # Python dependencies
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker Compose config
├── .env.example              # Environment template
└── README.md                 # This file
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get your API key from: https://makersuite.google.com/app/apikey

### Master Resume Template

Your `data/master.tex` should be a complete, valid LaTeX document. The AI will:
- Analyze the job description
- Identify relevant skills and experience
- Rewrite sections to emphasize matching qualifications
- Maintain your LaTeX formatting and structure

## How It Works

1. **Fetch Job Description**: Scrapes job posting URL or reads from file
2. **Load Master Resume**: Reads your LaTeX resume template
3. **AI Tailoring**: Sends both to Gemini Pro with tailoring instructions
4. **Compile PDF**: Runs `pdflatex` to generate final PDF
5. **Save Output**: Names file based on company name and date

## API Key Setup

### Getting a Gemini API Key

1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key to your `.env` file

### Free Tier Limits

- 60 requests per minute
- Sufficient for personal use
- No credit card required

## Troubleshooting

### "pdflatex not found"

**Docker**: Make sure you're using `docker-compose run tailor` (not `python main.py` directly)

**Local**: Install TeX Live:
- **Ubuntu/Debian**: `sudo apt-get install texlive-latex-extra`
- **macOS**: Install MacTeX from https://www.tug.org/mactex/
- **Windows**: Install MiKTeX from https://miktex.org/

### "GOOGLE_API_KEY not found"

Make sure:
1. You created `.env` file (not `.env.example`)
2. The key is on the line `GOOGLE_API_KEY=your_actual_key`
3. No quotes around the key value

### "LaTeX compilation failed"

Check the `.log` file in `output/` for details. Common issues:
- Missing LaTeX packages (install `texlive-latex-extra`)
- Invalid LaTeX syntax in your master resume
- Special characters not properly escaped

### "Failed to fetch URL"

- Check your internet connection
- Some job sites block automated requests
- Try saving the job description to a text file and use `--file` instead

## Development

### Running Tests

```bash
# Test job scraper
python -m core.jd_scraper

# Test Gemini client (requires API key)
python -m core.llm_client

# Test LaTeX compiler (requires pdflatex)
python -m core.latex_compiler
```

### Code Structure

- **jd_scraper.py**: Handles fetching and cleaning job descriptions
- **llm_client.py**: Manages Gemini API calls with retry logic
- **latex_compiler.py**: LaTeX compilation and file management
- **main.py**: CLI orchestration and user interface

## Tips for Best Results

1. **Quality Master Resume**: Start with a comprehensive, well-formatted LaTeX resume
2. **Full Job Descriptions**: Provide complete JDs with requirements and responsibilities
3. **Review Output**: Always review the tailored resume before submitting
4. **Iterate**: You may need to adjust your master resume based on results
5. **Keep Backups**: The tool doesn't modify your master resume

## Contributing

Found a bug or have a feature request? Please open an issue or submit a pull request.

## License

MIT

## Related Projects

- [AutoCareer Main Project](../../../README.md) - Full job application automation SaaS
- Frontend interface coming soon!

## Support

For questions or issues:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review the [spec.md](../../../spec.md) for detailed architecture
3. Open an issue on GitHub
