# Job Scraper Service

Headless browser service for fetching job pages using Playwright.

📚 **Full documentation**: See [docs/](../../../docs/)

## Quick Development Setup

```bash
cd backend/services/job-scraper
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
```
  "url": "https://www.linkedin.com/jobs/view/..."
}
```

**Format Options:**
- `text` (default): Clean text with HTML stripped
- `html`: Cleaned HTML preserving structure and links (used for job discovery)
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
