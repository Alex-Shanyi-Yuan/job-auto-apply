# Job Discovery Feature

## Overview

The Job Discovery feature is AutoCareer's intelligent job sourcing system that automatically finds, extracts, and scores job listings from multiple job boards. Using AI-powered agents and a plugin-based scraper architecture, it processes search result pages to generate personalized job suggestions.

## How AI Discovery Works

### JobDiscoveryAgent

The `JobDiscoveryAgent` is the core AI component that extracts job listings from HTML content. Located in `backend/services/resume-tailor/core/agents.py`, it:

1. **Receives cleaned HTML** from job board search results pages
2. **Analyzes the structure** to identify job listing patterns (cards, lists, repeated elements)
3. **Extracts key information** for each job:
   - Job title
   - Company name (defaults to "Unknown Company" if not found)
   - Direct URL to the job posting (not the search results page)
4. **Applies filters** based on user-defined criteria
5. **Returns structured data** as a list of `DiscoveredJob` objects

**AI Prompt Strategy:**
- Temperature set to 0.1 for consistent, deterministic extraction
- HTML truncated to ~40k characters to fit within token limits
- Uses Google Gemini Pro via structured output (Pydantic schemas)
- Handles both absolute and relative URLs (resolution happens later)

### Discovery Pipeline Flow

```
Source URL → Scraper Plugin → HTML → JobDiscoveryAgent → Discovered Jobs 
→ URL Resolution → Individual Job Pages → JobScoringAgent → Saved Suggestions
```

## Source Configuration

### JobSource Model

Each job source represents a job board search URL to monitor. Stored in the `jobsource` table:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Integer | Unique identifier |
| `url` | String | The search results page URL |
| `name` | String | Friendly name (e.g., "LinkedIn - Python Jobs") |
| `filter_prompt` | String (optional) | Source-specific AI filter criteria |
| `last_scraped_at` | Datetime | Timestamp of last scan |
| `created_at` | Datetime | Source creation timestamp |
| `updated_at` | Datetime | Last modification timestamp |

### Configuration Example

**Via Frontend UI (Suggestions Page):**
1. Navigate to `/suggestions`
2. Expand the "Job Sources" section
3. Fill in the form:
   - **Name:** "LinkedIn Senior Software Engineer"
   - **URL:** `https://www.linkedin.com/jobs/search/?keywords=senior%20software%20engineer`
   - **Source Filter (optional):** "Focus on remote-friendly companies with strong engineering culture"
4. Click "Add Source"

**Via API:**
```bash
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.linkedin.com/jobs/search/?keywords=python",
    "name": "LinkedIn Python Jobs",
    "filter_prompt": "Backend roles with Python and cloud experience"
  }'
```

## Global Filter vs Source-Specific Filters

AutoCareer supports two levels of filtering:

### Global Filter
- **Applies to ALL sources** during every scan
- Set once in the purple card at the top of `/suggestions`
- Used to define general criteria like:
  - Desired job titles and roles
  - Required skills or technologies
  - Location preferences (remote, specific cities)
  - Company size or type preferences
- **Example:** "Remote software engineering roles focusing on backend development with Python, Go, or Rust. Prefer startups or mid-size tech companies."

### Source-Specific Filters
- **Optional per-source refinements**
- Applied in addition to the global filter
- Useful for tailoring searches to specific job boards
- **Example for a startup-focused source:** "Prioritize early-stage companies (Series A-C) with equity compensation"

**Filter Logic:**
Both filters are concatenated and passed to the `JobDiscoveryAgent` prompt. The AI interprets them as AND conditions—a job must match both the global criteria and any source-specific criteria to be included.

## Scraper Plugin Architecture

AutoCareer uses a **plugin-based scraper system** to handle site-specific extraction logic. This design solves the problem of "one-size-fits-all" scraping that fails on diverse job boards.

### Why Plugins?

Job sites vary widely:
- **Server-rendered sites** (simple, fast to load)
- **JavaScript-heavy sites** (need custom wait selectors)
- **Sites with redirects or wrapped links** (require URL recovery)
- **Rate-limited sites** (need specific scraping strategies)

Generic scraping strategies cause:
- Discovery loss (jobs not extracted)
- URL resolution failures (can't find actual job page)
- Hard-to-debug errors

### Plugin Architecture Components

Each plugin is a Python package in `backend/services/job-scraper/plugins/` with:

1. **`plugin.json` (Manifest)**
   - Metadata and routing rules
   - Domain matching patterns
   - Scraping configuration

2. **`extractor.py` (Extraction Logic)**
   - Site-specific HTML hints or transformations
   - Custom element selection if needed

3. **`resolver.py` (URL Resolution)**
   - Converts relative URLs to absolute
   - Handles site-specific link patterns (e.g., tracking redirects)
   - Normalizes URL formats

### Plugin Manifest Structure

Example from `plugins/linkedin/plugin.json`:

```json
{
  "name": "linkedin",
  "version": "1.0.0",
  "domains": ["linkedin.com", "www.linkedin.com", "jobs.linkedin.com"],
  "extractor_module": "extractor",
  "resolver_module": "resolver",
  "pagination_strategy": "none",
  "requires_login": false
}
```

**Key Fields:**
- `domains`: List of domain patterns to match for plugin selection
- `extractor_module`: Python module name for extraction logic
- `resolver_module`: Python module name for URL resolution
- `pagination_strategy`: How to handle multi-page results (v1: "none")
- `requires_login`: Whether site needs authentication (v1: false)

### Plugin Registry and Routing

The `plugin_registry.py` module:
1. **Loads all plugin manifests** at scraper service startup
2. **Validates schemas** using `plugin_schema.py`
3. **Builds a domain-to-plugin mapping**
4. **Routes scrape requests** to the appropriate plugin based on URL domain
5. **Falls back to generic plugin** if no match exists

**Startup Logging:**
```
[INFO] Loading scraper plugins...
[INFO] Loaded plugin: linkedin (v1.0.0) - domains: linkedin.com, www.linkedin.com
[INFO] Loaded plugin: google_jobs (v1.0.0) - domains: google.com, www.google.com
[INFO] Plugin registry initialized with 7 plugins
```

## Supported Job Sites

AutoCareer currently has dedicated plugins for **6 major job sites/companies**:

| Plugin | Domains | Purpose |
|--------|---------|---------|
| **LinkedIn** | `linkedin.com`, `www.linkedin.com`, `jobs.linkedin.com` | General job board with extensive listings |
| **Google Jobs** | `google.com`, `www.google.com` | Google's job search aggregator |
| **OpenAI** | `openai.com`, `www.openai.com`, `jobs.openai.com`, `boards.greenhouse.io` | OpenAI careers + Greenhouse integration |
| **Anthropic** | `anthropic.com`, `www.anthropic.com`, `jobs.anthropic.com` | Anthropic career pages |
| **Netflix** | `netflix.com`, `jobs.netflix.com` | Netflix career portal |
| **Jane Street** | `janestreet.com`, `www.janestreet.com`, `jobs.janestreet.com` | Finance/trading firm careers |
| **Generic** | *(fallback)* | Default plugin for any unsupported site |

**Note:** The generic plugin uses a best-effort approach that works reasonably well for many sites but may miss jobs on complex or non-standard pages.

## Parallel Processing

AutoCareer uses parallelism at two levels to maximize scan speed:

### Level 1: Parallel Source Scanning

**Environment Variable:** `MAX_CONCURRENT_SOURCES` (default: 5)

Multiple job sources are processed simultaneously. For example, if you have 10 sources configured:
- Sources 1-5 start scanning immediately
- As each completes, the next source begins
- All sources are scanned in ~2x the time of a single source

**Located in:** `backend/services/resume-tailor/server.py` → `process_job_discovery()`

```python
# Parallel source processing with concurrency limit
with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SOURCES) as executor:
    futures = [
        executor.submit(process_single_source, source, global_filter)
        for source in sources_to_scan
    ]
```

### Level 2: Parallel Job Scoring (Within Each Source)

**Environment Variable:** `MAX_CONCURRENT_JOBS` (default: 10)

After the `JobDiscoveryAgent` extracts jobs from a source page, individual jobs are:
1. **Scraped** for full job descriptions (in parallel)
2. **Scored** by the `JobScoringAgent` (in parallel)

**Located in:** `backend/services/resume-tailor/server.py` → `process_single_source()`

```python
# Parallel job scraping and scoring within a source
with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_JOBS) as executor:
    score_futures = [
        executor.submit(scrape_and_score_job, discovered_job)
        for discovered_job in discovered_jobs
    ]
```

### Rate Limiting

**Environment Variable:** `RATE_LIMIT_DELAY` (default: 0.2 seconds)

A configurable delay between job page scrapes to avoid overwhelming job sites or triggering rate limits.

### Performance Example

With 3 sources, 50 jobs discovered per source, default settings:
- **Sequential processing:** ~10 minutes
- **With parallel processing:** ~2-3 minutes
- **Bottleneck:** AI scoring API latency (Gemini Pro)

## URL Resolution

Job boards often use complex URL patterns that need normalization:

### The Problem

Extracted URLs can be:
- **Relative:** `/jobs/12345` (needs base URL)
- **Wrapped:** `https://jobboard.com/redirect?url=...` (needs unwrapping)
- **Tracking links:** `https://jobboard.com/out?id=xyz&redirect=...` (needs parsing)
- **Already absolute:** `https://company.com/careers/job/456` (use as-is)

### Resolution Process

**Function:** `resolve_job_url(url: str, source_url: str, plugin_name: str) -> str`

1. **Plugin-based resolution:** Delegates to the plugin's `resolver.py`
2. **Fallback to generic:** If plugin has no custom resolver
3. **Base URL calculation:** Extracts scheme + domain from source URL
4. **Relative URL handling:** Uses `urllib.parse.urljoin()` to combine base + relative

**Example:**
```python
source_url = "https://linkedin.com/jobs/search?keywords=python"
relative_url = "/jobs/view/12345"

# Result: "https://linkedin.com/jobs/view/12345"
resolved_url = resolve_job_url(relative_url, source_url, "linkedin")
```

### Plugin-Specific Resolution

Some plugins implement custom URL normalization:
- **LinkedIn:** Strips tracking parameters, normalizes job ID format
- **Google Jobs:** Extracts the actual employer URL from Google's redirect
- **Greenhouse:** Resolves company-specific Greenhouse board URLs

## Scan Reports

After each discovery scan, AutoCareer generates a detailed scan report showing what happened.

### Report Structure

**Located in:** `GET /suggestions/status` response → `source_results[]`

Each source in the scan produces a `SourceScanResult`:

```typescript
interface SourceScanResult {
  source_id: number;
  source_name: string;
  plugin_used: string;          // e.g., "linkedin", "generic"
  added_jobs: number;            // New jobs saved as suggestions
  skipped_jobs: number;          // Jobs not saved (duplicates or low score)
  total_discovered: number;      // Total jobs extracted from page
  error?: string;                // Error message if scan failed
  skip_reasons: {
    "Low Score": number;         // Jobs with score below threshold
    "Already Existed": number;   // Duplicate job URLs
  };
}
```

### Frontend Display

The scan report modal (`/suggestions` page) shows:

**Summary:**
- Total sources scanned
- Total jobs added across all sources
- Total jobs skipped

**Per-Source Results:**

For each source:
- ✅ **Added Jobs:** Green badge with count
- 📊 **Total Discovered:** Gray text
- ⏭️ **Skipped Jobs:** Expandable section showing:
  - **"Low Score"** – Orange badge (jobs below relevance threshold)
  - **"Already Existed"** – Gray badge (duplicates from previous scans)

**Example:**

```
Scan Report - 3 sources scanned

LinkedIn Python Jobs
  Plugin: linkedin
  ✅ Added: 12 jobs
  📊 Discovered: 25 jobs
  ⏭️ Skipped: 13 jobs
    🟠 Low Score: 10 jobs (score < 50)
    ⚪ Already Existed: 3 jobs

Google Jobs Remote SWE
  Plugin: google_jobs
  ✅ Added: 8 jobs
  📊 Discovered: 20 jobs
  ⏭️ Skipped: 12 jobs
    🟠 Low Score: 12 jobs (score < 50)
```

### Scan Status Polling

**Frontend behavior:**
1. User clicks "Refresh Suggestions" or "Scan Selected Sources"
2. `POST /suggestions/refresh` triggers background scan
3. Frontend polls `GET /suggestions/status` every 2 seconds
4. Progress panel shows:
   - "Scanning X sources..."
   - Current scan progress (if available)
5. When `is_scanning: false`, polling stops
6. Scan report modal automatically opens with results

### Viewing Past Reports

**"View Last Report" Button:**
- Persists the most recent scan results in component state
- Available even after page refresh (stored in backend scan status)
- Allows users to review what happened without re-scanning

## Best Practices

### Configuring Effective Sources

1. **Use specific search URLs** with pre-filtered criteria (location, job level, keywords)
2. **Avoid overly broad searches** – narrows down AI extraction, reduces noise
3. **Test sources individually first** before adding to multi-source scans
4. **Monitor scan reports** to identify low-performing sources

### Writing Effective Filters

**Global Filter Template:**
```
I'm looking for [job titles] roles in [industry/domain].

Required skills: [skill 1], [skill 2], [skill 3]
Preferred: [nice-to-have skills or experience]

Location: [Remote / City name / Hybrid]
Company type: [Startup / Enterprise / Non-profit]

Exclude: [roles or industries to avoid]
```

**Source-Specific Filter Examples:**
- "Prioritize senior-level positions (5+ years experience)"
- "Focus on companies with strong open-source culture"
- "Only roles offering visa sponsorship"

### Optimizing Scan Performance

1. **Limit active sources** to 10-15 high-quality boards
2. **Use source-specific filters** to reduce irrelevant job extraction
3. **Increase concurrency** if you have a powerful server:
   ```bash
   MAX_CONCURRENT_SOURCES=10
   MAX_CONCURRENT_JOBS=20
   ```
4. **Monitor rate limits** – reduce `RATE_LIMIT_DELAY` if job boards are responsive

### Troubleshooting

**"No jobs discovered from source X"**
- Check if the URL is a search results page (not a single job page)
- Verify the site isn't blocking automated access
- Look at scan report for plugin errors
- Try the generic plugin if a dedicated plugin is failing

**"All jobs skipped as 'Already Existed'"**
- This is normal for subsequent scans of the same source
- Job URLs are unique – duplicate URLs are filtered out
- Use a broader search or add new sources for fresh jobs

**"All jobs skipped as 'Low Score'"**
- Your global filter may be too restrictive
- The source's jobs may not match your resume well
- Try adjusting filter criteria or choosing different job boards
- Review your master resume to ensure relevant skills are included

## API Reference

### Discovery Endpoints

**Trigger a Scan:**
```http
POST /suggestions/refresh
Content-Type: application/json

{
  "source_ids": [1, 2, 3]  // Optional: scan specific sources only
}

Response: { "status": "scanning" }
```

**Get Scan Status:**
```http
GET /suggestions/status

Response: {
  "is_scanning": true,
  "current_source": "LinkedIn Python Jobs",
  "progress": 2,
  "total": 5,
  "source_results": [
    {
      "source_id": 1,
      "source_name": "LinkedIn Python Jobs",
      "plugin_used": "linkedin",
      "added_jobs": 12,
      "skipped_jobs": 8,
      "total_discovered": 20,
      "skip_reasons": {
        "Low Score": 5,
        "Already Existed": 3
      }
    }
  ]
}
```

**Get Suggestions:**
```http
GET /suggestions

Response: [
  {
    "id": 42,
    "url": "https://linkedin.com/jobs/view/12345",
    "company": "TechCorp",
    "title": "Senior Backend Engineer",
    "status": "suggested",
    "score": 85,
    "source_id": 1,
    "created_at": "2024-04-04T10:30:00"
  }
]
```

### Source Management Endpoints

**List Sources:**
```http
GET /sources
```

**Create Source:**
```http
POST /sources
Content-Type: application/json

{
  "url": "https://linkedin.com/jobs/search?keywords=python",
  "name": "LinkedIn Python Jobs",
  "filter_prompt": "Backend roles with cloud experience"
}
```

**Update Source:**
```http
PUT /sources/{source_id}
Content-Type: application/json

{
  "name": "Updated Name",
  "url": "https://...",
  "filter_prompt": "..."
}
```

**Delete Source:**
```http
DELETE /sources/{source_id}
```

### Filter Management

**Get Global Filter:**
```http
GET /settings/global-filter

Response: {
  "value": "Remote software engineering roles..."
}
```

**Update Global Filter:**
```http
PUT /settings/global-filter
Content-Type: application/json

{
  "value": "Remote software engineering roles focusing on backend..."
}
```

## Future Enhancements

Planned improvements to the discovery system:

1. **Pagination Support** – Scrape multiple pages of search results
2. **Authenticated Scraping** – Support job boards requiring login
3. **Plugin Health Dashboard** – Monitor plugin performance and failures
4. **Smart Re-scanning** – Only scan sources with likely new content
5. **Discovery Analytics** – Track which sources yield best matches
6. **Custom Plugin Authoring UI** – Create plugins without editing code
7. **Incremental Discovery** – Only process new jobs since last scan

## Related Documentation

- [Resume Tailoring](./resume-tailoring.md) – What happens after a job is discovered
- [Application Tracking](./application-tracking.md) – Managing job statuses and workflow
- [Scraper Plugin Design Doc](../../SCRAPER_PLUGIN_DESIGN_DOC.md) – Detailed plugin architecture
