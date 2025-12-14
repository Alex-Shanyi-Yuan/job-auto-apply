# Job Scraper Service

A specialized microservice for fetching and extracting text content from job posting URLs using Playwright and BeautifulSoup.

## Features

- 🕷️ **Headless Browsing**: Uses Playwright (Chromium) to render dynamic JavaScript-heavy websites.
- 🧹 **Clean Extraction**: Uses BeautifulSoup to strip HTML tags and scripts, returning clean text.
- 🚀 **FastAPI**: Exposes a simple REST API for easy integration.
- 🐳 **Dockerized**: Pre-configured with all browser dependencies.

## API Endpoints

### `POST /scrape`

Scrapes a given URL and returns the title and text content.

**Request:**
```json
{
  "url": "https://www.linkedin.com/jobs/view/..."
}
```

**Response:**
```json
{
  "title": "Software Engineer - Company Name",
  "text": "Job Description text content...",
  "url": "https://www.linkedin.com/jobs/view/..."
}
```

## Local Development

### Using Docker (Recommended)

The service is designed to run within the main Docker Compose stack.

```bash
# From project root
docker-compose up scraper
```

The service will be available at `http://localhost:8001`.

### Manual Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

2. **Run Server**
   ```bash
   uvicorn main:app --reload --port 8001
   ```
