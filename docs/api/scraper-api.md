# Scraper API Documentation

The Job Scraper Service provides a simple API for fetching job pages using Playwright (headless Chrome).

## Endpoint

### POST /scrape

Fetches a job page and returns cleaned content.

**Request Schema:**

```json
{
  "url": "string",
  "format": "text" | "html"  // Optional, defaults to "text"
}
```

**Response Schema:**

```json
{
  "title": "string",
  "text": "string",
  "url": "string"
}
```

## Request Parameters

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | string | Yes | The job posting URL to scrape |
| `format` | string | No | Output format: `"text"` for clean text (default), `"html"` for cleaned HTML with links |

## Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Page title or job title |
| `text` | string | Cleaned content (text or HTML based on format parameter) |
| `url` | string | The URL that was scraped |

## Examples

### Basic Text Scraping

**Request:**

```bash
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/jobs/view/1234567890",
    "format": "text"
  }'
```

**Response:**

```json
{
  "title": "Senior Software Engineer - AI/ML",
  "text": "We are seeking a Senior Software Engineer to join our AI/ML team...",
  "url": "https://www.linkedin.com/jobs/view/1234567890"
}
```

### HTML Format

**Request:**

```bash
curl -X POST http://localhost:8001/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://jobs.google.com/j/abc123",
    "format": "html"
  }'
```

**Response:**

```json
{
  "title": "Product Manager - Search",
  "text": "<div><h1>About the Role</h1><p>We are looking for...</p></div>",
  "url": "https://jobs.google.com/j/abc123"
}
```

## Plugin System

The scraper uses a plugin registry to handle site-specific extraction logic:

- **Domain Manifests**: Each supported site has a plugin in `plugins/` directory
- **Auto-Selection**: The scraper automatically selects the right plugin based on URL domain
- **Fallback**: If no plugin matches, uses generic HTML parsing

### Supported Sites

The scraper has optimized plugins for:
- Google Careers
- LinkedIn Jobs
- Netflix Jobs
- Jane Street Careers
- OpenAI Careers
- Anthropic Careers

See [Job Discovery documentation](../features/job-discovery.md#scraper-plugins) for details on adding new plugins.

## Configuration

### Browser Settings

The scraper uses Playwright with Chromium:

```python
# User agent
"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# Headless mode: True
# Wait strategy: domcontentloaded
# Timeout: 60 seconds
```

### Wait Time

Dynamic content waits 3 seconds after page load to ensure JavaScript executes.

## Error Handling

The scraper returns HTTP 500 with error details if:
- URL is unreachable
- Page load timeout (>60 seconds)
- JavaScript errors prevent content loading
- Invalid URL format

**Error Response:**

```json
{
  "detail": "Error scraping URL: Connection timeout"
}
```

## Performance Notes

- **Memory**: Each scrape launches a new browser instance (~500MB RAM)
- **Concurrency**: Limited by `MAX_CONCURRENT_JOBS` in tailor service
- **Rate Limiting**: Some sites may block excessive requests

## Health Check

Check if the scraper service is running:

```bash
curl http://localhost:8001/health
```

Expected response:

```json
{
  "status": "ok"
}
```

## Integration

The Resume Tailor Service calls this API internally:

```python
# backend/services/resume-tailor/core/jd_scraper.py
async with httpx.AsyncClient() as client:
    response = await client.post(
        f"{SCRAPER_SERVICE_URL}/scrape",
        json={"url": job_url, "format": "text"}
    )
    data = response.json()
    job_description = data["text"]
```

## See Also

- **[Job Discovery](../features/job-discovery.md)** - How scraping fits into job discovery
- **[Environment Setup](../getting-started/environment-setup.md#service-urls)** - Configure `SCRAPER_SERVICE_URL`
- **[Deployment Guide](../getting-started/deployment.md)** - Running the scraper service
