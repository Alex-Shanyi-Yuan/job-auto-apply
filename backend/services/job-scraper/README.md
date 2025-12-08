# Job Scraper Service

This service is responsible for scraping job listings from various job boards and company websites. It uses **Playwright** to handle dynamic content (SPAs) and **Pydantic** for data validation.

## Features

*   **Dynamic Scraping:** Uses Playwright (Chromium) to render JavaScript-heavy websites.
*   **Standardized Output:** All scrapers return data in a consistent `JobPosting` format.
*   **Dockerized:** Fully containerized environment including all browser dependencies.
*   **Modular:** Easy to add new scrapers by extending the `BaseScraper` class.

## Supported Scrapers

*   **YCombinator (Hacker News Jobs):** Scrapes the latest job postings from `news.ycombinator.com/jobs`.

## Project Structure

```
backend/services/job-scraper/
├── scrapers/               # Individual scraper implementations
│   ├── base.py             # Abstract base class
│   └── ycombinator.py      # YC implementation
├── models.py               # Pydantic data models
├── main.py                 # CLI entry point
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose configuration
└── requirements.txt        # Python dependencies
```

## Usage

### Option 1: Docker (Recommended)

The easiest way to run the scraper is using Docker, as it handles all the browser dependencies for you.

**1. Build the image:**
```bash
docker-compose build
```

**2. Run the default scraper (YCombinator):**
```bash
docker-compose run --rm scraper
```

**3. Run with custom arguments:**
```bash
# Scrape a specific URL
docker-compose run --rm scraper --scraper ycombinator --url "https://news.ycombinator.com/jobs?p=2"
```

### Option 2: Local Development

If you prefer to run it locally, you need to install Python dependencies and Playwright browsers.

**1. Install dependencies:**
```bash
pip install -r requirements.txt
```

**2. Install Playwright browsers:**
```bash
playwright install
```

**3. Run the scraper:**
```bash
python main.py --scraper ycombinator
```

## Data Model

Each scraped job returns the following JSON structure:

```json
{
  "title": "Senior Software Engineer",
  "company": "Startup Inc",
  "location": "Remote",
  "job_url": "https://...",
  "salary_range": "$150k - $200k",
  "description": "...",
  "posted_date": "2023-10-27",
  "source": "YCombinator",
  "scraped_at": "2023-10-27T10:00:00Z"
}
```
