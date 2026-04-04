# Testing Strategies

This guide covers testing approaches for AutoCareer, with a focus on AI agent testing, stub modes, and manual workflows. Unit and integration tests will be added in future iterations.

## Overview

AutoCareer includes AI-powered components (job discovery, scoring, parsing, tailoring) that require special testing strategies. This guide covers:

- **Stub Mode Testing** — Test agent logic without API costs
- **Manual Testing Workflows** — Verify end-to-end functionality
- **Database Backend Testing** — Test with SQLite, PostgreSQL, or hybrid
- **Future Testing Plans** — Unit tests, integration tests, CI/CD

## Agent Testing with Stub Mode

### What is Stub Mode?

Stub mode replaces Google Gemini API calls with **mock responses**. This allows you to:

- ✅ Test agent logic without API costs
- ✅ Develop offline or without API keys
- ✅ Run fast, deterministic tests
- ✅ Debug edge cases (e.g., malformed responses)

### Enabling Stub Mode

Set the environment variable before starting the backend:

```bash
# With Docker
RESUME_TAILOR_LLM_MODE=stub docker-compose up tailor

# Without Docker
cd backend/services/resume-tailor
RESUME_TAILOR_LLM_MODE=stub uvicorn server:app --reload --port 8000
```

**In `.env`:**
```bash
RESUME_TAILOR_LLM_MODE=stub
```

### How Stub Mode Works

The `LLMClient` in `core/llm_client.py` checks the mode:

```python
if self.mode == "stub":
    return self._generate_stub_response(response_model)
else:
    return await self._call_gemini_api(prompt, response_model)
```

**Stub responses** are hardcoded examples that match the Pydantic schema:

```python
def _generate_stub_response(self, response_model):
    if response_model == JobDiscoveryOutput:
        return JobDiscoveryOutput(jobs=[
            {"title": "Software Engineer", "company": "Acme Corp", "url": "/jobs/123"}
        ])
    elif response_model == JobScoringOutput:
        return JobScoringOutput(score=85, reasoning="Strong match")
    # ...
```

### Testing Discovery Agent with Stub Mode

**Start backend with stub mode:**
```bash
RESUME_TAILOR_LLM_MODE=stub uvicorn server:app --reload
```

**Trigger discovery scan:**
```bash
curl -X POST http://localhost:8000/suggestions/refresh \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected behavior:**
- Discovery agent returns mock jobs
- Scoring agent assigns score of 85 to all jobs
- Jobs saved to database with `status="suggested"`
- No API calls made (check logs for absence of Gemini requests)

**Verify:**
```bash
# Check suggestions
curl http://localhost:8000/suggestions

# Should return stub jobs with score=85
```

### Testing Tailoring Agent with Stub Mode

**Submit a job for tailoring:**
```bash
curl -X POST http://localhost:8000/apply \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/job/123", "resume_text": "..."}'
```

**Expected behavior:**
- Parsing agent returns stub requirements
- Tailoring agent returns mock LaTeX with minor changes
- PDF compilation succeeds (or fails if TeX Live not installed)
- Job status changes to `applied`

### Customizing Stub Responses

Edit `core/llm_client.py` to return custom stub data:

```python
def _generate_stub_response(self, response_model):
    if response_model == JobDiscoveryOutput:
        # Add more jobs for testing pagination
        return JobDiscoveryOutput(jobs=[
            {"title": f"Job {i}", "company": f"Company {i}", "url": f"/job/{i}"}
            for i in range(20)
        ])
    # ...
```

### Limitations of Stub Mode

- ❌ Doesn't test actual LLM behavior (prompt quality, edge cases)
- ❌ Doesn't catch API errors (rate limits, malformed responses)
- ❌ Doesn't verify prompt engineering effectiveness

**Use stub mode for:**
- 🎯 Logic testing (e.g., job deduplication, filtering)
- 🎯 Database operations
- 🎯 API endpoint validation
- 🎯 Frontend integration testing

**Use real API for:**
- 🎯 Prompt refinement
- 🎯 Quality assurance
- 🎯 Production readiness

## Dry-Run Testing (Future Feature)

**Status:** Planned for Feature 8

When implemented, dry-run mode will:
- Perform all discovery steps except saving to database
- Return preview of jobs that would be added
- Allow testing filter prompts without polluting database

**Planned usage:**
```bash
curl -X POST http://localhost:8000/suggestions/refresh?dry_run=true
```

## Manual Testing Workflow

### Full Stack Testing

**1. Start all services:**
```bash
docker-compose up --build
```

**2. Verify services are running:**
```bash
curl http://localhost:8000/health      # Backend
curl http://localhost:8001/health      # Scraper (if endpoint exists)
curl http://localhost:3000             # Frontend (should return HTML)
```

**3. Test discovery flow:**

**a. Configure sources:**
- Open http://localhost:3000/suggestions
- Add a job board URL (e.g., `https://www.ycombinator.com/jobs`)
- Set global filter (e.g., "Python backend engineer")

**b. Run discovery scan:**
- Click "Refresh Suggestions"
- Monitor scan progress panel
- Wait for completion (check "View Last Report")

**c. Verify results:**
- Jobs appear with score badges
- Scores are reasonable (0-100)
- URLs are valid (not relative paths)

**4. Test apply flow:**

**a. Apply to a job:**
- Click "Apply" on a suggested job
- Job status changes to "processing"

**b. Monitor progress:**
- View backend logs: `docker-compose logs -f tailor`
- Check for scraper requests, agent calls, PDF compilation

**c. Verify completion:**
- Job status changes to "applied"
- PDF download link appears
- PDF downloads successfully

**5. Test error handling:**

**a. Invalid URL:**
- Submit `https://invalid-url` via `/apply` page
- Verify job status changes to "failed"
- Error message is visible

**b. Scraper failure:**
- Submit a URL that blocks headless browsers
- Verify graceful failure with error message

### Frontend Testing

**Without backend (component testing):**
```bash
cd frontend
npm run dev
# Test UI components in isolation
```

**Linting:**
```bash
npm run lint
npm run lint -- --fix  # Auto-fix issues
```

**Type checking:**
```bash
npm run build  # Will fail on TypeScript errors
```

### Backend Testing

**Test individual endpoints:**

```bash
# Health check
curl http://localhost:8000/health

# List sources
curl http://localhost:8000/sources

# Add source
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/jobs", "name": "Example Jobs"}'

# Get suggestions
curl http://localhost:8000/suggestions

# Trigger scan
curl -X POST http://localhost:8000/suggestions/refresh

# Check scan status
curl http://localhost:8000/suggestions/status
```

**Interactive API testing:**
- Open http://localhost:8000/docs (Swagger UI)
- Test endpoints with built-in forms
- View request/response schemas

### Database Testing

**Test with SQLite:**
```bash
# Set backend to SQLite
echo "DATABASE_BACKEND=sqlite" >> .env
docker-compose up tailor

# Verify database file created
ls backend/services/resume-tailor/data/autocareer.db

# Inspect schema
docker-compose exec tailor sqlite3 data/autocareer.db ".schema job"
```

**Test with PostgreSQL:**
```bash
# Set backend to PostgreSQL
echo "DATABASE_BACKEND=postgres" >> .env
docker-compose up postgres tailor

# Verify connection
docker-compose exec postgres psql -U postgres -d autocareer -c "\dt"
```

**Test hybrid mode:**
```bash
# Set backend to hybrid
cat << EOF >> .env
DATABASE_BACKEND=hybrid
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true
SYNC_ON_SHUTDOWN=true
EOF

docker-compose up --build

# Add data via API
curl -X POST http://localhost:8000/sources \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "name": "Test"}'

# Shutdown (syncs SQLite → PostgreSQL)
docker-compose down

# Verify data in PostgreSQL
docker-compose up postgres
docker-compose exec postgres psql -U postgres -d autocareer -c "SELECT * FROM jobsource;"
```

## Testing AI Components

### Testing Prompts

**Prompt engineering workflow:**

1. **Edit agent prompt:**
   - Open `backend/services/resume-tailor/core/agents.py`
   - Modify system prompt or few-shot examples

2. **Test with real API:**
   ```bash
   # Remove stub mode
   unset RESUME_TAILOR_LLM_MODE
   uvicorn server:app --reload
   ```

3. **Run discovery on a small source:**
   ```bash
   # Limit to 1 source to save API costs
   curl -X POST http://localhost:8000/suggestions/refresh
   ```

4. **Review agent output:**
   - Check logs for extracted jobs
   - Verify scores are reasonable
   - Inspect reasoning in database

5. **Iterate on prompt:**
   - Adjust prompt based on output quality
   - Repeat steps 3-4

### Testing Structured Output

Agents use **Pydantic models** to enforce JSON schemas:

```python
class JobDiscoveryOutput(BaseModel):
    jobs: List[Dict[str, str]]  # Must be list of dicts with string values
```

**Test schema validation:**

```python
# In Python REPL or test file
from core.agents import JobDiscoveryAgent, JobDiscoveryOutput

# Valid output
output = JobDiscoveryOutput(jobs=[
    {"title": "Engineer", "company": "Acme", "url": "/jobs/1"}
])

# Invalid output (will raise ValidationError)
output = JobDiscoveryOutput(jobs=[
    {"title": 123}  # title must be string
])
```

**Pydantic catches:**
- Missing required fields
- Wrong data types
- Extra fields (if `Extra.forbid` is set)

### Testing Rate Limits

**Configure rate limiting:**
```bash
# In .env
RATE_LIMIT_DELAY=2.0              # 2 seconds between scrapes
MAX_CONCURRENT_JOBS=5             # Max 5 parallel jobs
MAX_CONCURRENT_SOURCES=2          # Max 2 parallel sources
```

**Test with high concurrency:**
```bash
# Add multiple sources
for i in {1..10}; do
  curl -X POST http://localhost:8000/sources \
    -H "Content-Type: application/json" \
    -d "{\"url\": \"https://example.com/jobs$i\", \"name\": \"Source $i\"}"
done

# Trigger scan (will process 2 at a time)
curl -X POST http://localhost:8000/suggestions/refresh

# Monitor logs for rate limiting
docker-compose logs -f tailor | grep "Rate limit"
```

## Future: Unit Tests

**Planned test structure:**

```
backend/services/resume-tailor/
└── tests/
    ├── test_agents.py           # Agent logic tests
    ├── test_api.py              # FastAPI endpoint tests
    ├── test_database.py         # SQLModel CRUD tests
    ├── test_llm_client.py       # LLM client tests (with mocks)
    └── fixtures/
        ├── sample_job_html.html
        └── sample_resume.tex
```

**Example unit test (pytest):**

```python
import pytest
from core.agents import JobScoringAgent, JobScoringOutput

def test_scoring_agent_stub_mode():
    agent = JobScoringAgent(llm_client=StubLLMClient())
    result = agent.score_job(job_description="...", resume="...")
    
    assert isinstance(result, JobScoringOutput)
    assert 0 <= result.score <= 100
    assert result.reasoning is not None
```

## Future: Integration Tests

**Planned scenarios:**

1. **End-to-end discovery flow:**
   - Add source → Trigger scan → Verify jobs in database

2. **End-to-end apply flow:**
   - Submit URL → Wait for processing → Verify PDF exists

3. **Hybrid mode sync:**
   - Add data to PostgreSQL → Sync to SQLite → Verify consistency

4. **Error recovery:**
   - Simulate API failures → Verify graceful degradation

## Testing Checklist

### Before Committing

- [ ] Linting passes (`npm run lint` for frontend)
- [ ] No TypeScript errors (`npm run build` for frontend)
- [ ] Backend runs without errors (`uvicorn server:app`)
- [ ] Migrations applied successfully (`alembic upgrade head`)

### Before Deploying

- [ ] Full stack runs (`docker-compose up --build`)
- [ ] Discovery scan completes successfully
- [ ] Apply flow generates PDF
- [ ] Database migrations applied
- [ ] Environment variables documented

### When Modifying Agents

- [ ] Test with stub mode first (logic validation)
- [ ] Test with real API on small dataset
- [ ] Review prompt output quality
- [ ] Check for edge cases (empty results, malformed HTML)
- [ ] Verify Pydantic schema validation

### When Changing Database Schema

- [ ] Migration created (`alembic revision --autogenerate`)
- [ ] Migration reviewed (check auto-generated SQL)
- [ ] Migration tested locally (upgrade + downgrade)
- [ ] Data migration added if needed
- [ ] Hybrid mode sync tested (if applicable)

## Troubleshooting Tests

### Frontend fails to connect to backend

**Cause:** Backend not running or wrong `NEXT_PUBLIC_API_URL`

**Fix:**
```bash
# Check backend
curl http://localhost:8000/health

# Update frontend/.env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > frontend/.env.local

# Restart frontend
cd frontend && npm run dev
```

### Stub mode still calling Gemini API

**Cause:** Environment variable not set correctly

**Fix:**
```bash
# Verify environment
docker-compose exec tailor printenv | grep LLM_MODE

# Should output: RESUME_TAILOR_LLM_MODE=stub

# If not, rebuild
RESUME_TAILOR_LLM_MODE=stub docker-compose up --build
```

### PDF compilation fails in tests

**Cause:** TeX Live not installed (only in Docker container)

**Fix:**
- Run `tailor` service in Docker for PDF tests
- Or skip PDF generation in local tests

### Database out of sync in hybrid mode

**Cause:** Sync failed or not configured

**Fix:**
```bash
# Manual sync PostgreSQL → SQLite
docker-compose exec tailor python -c "
from core.db_sync import sync_postgres_to_sqlite
sync_postgres_to_sqlite()
"

# Verify data
docker-compose exec tailor sqlite3 data/autocareer.db "SELECT COUNT(*) FROM job;"
```

## Performance Testing

### Measure discovery scan time

```bash
# Start timer
time curl -X POST http://localhost:8000/suggestions/refresh

# Check logs for timing
docker-compose logs tailor | grep "Scan completed"
```

### Monitor API costs

```bash
# Count API calls in logs
docker-compose logs tailor | grep "Gemini API call" | wc -l

# Estimate cost
# Gemini Pro: ~$0.00025 per 1K input tokens, ~$0.0005 per 1K output tokens
```

### Database query performance

```bash
# Enable SQLite query logging
docker-compose exec tailor sqlite3 data/autocareer.db

# In SQLite shell
PRAGMA query_only = ON;
.eqp on  # Enable query plan
SELECT * FROM job WHERE score > 80 ORDER BY score DESC;
```

## Best Practices

1. **Test with stub mode first** — Fast iteration without API costs
2. **Use real API sparingly** — Small datasets to verify prompt quality
3. **Verify database state** — Check data after operations
4. **Monitor logs** — Watch for errors, rate limits, API calls
5. **Test error paths** — Invalid URLs, malformed responses, API failures
6. **Document test scenarios** — Add examples to this guide

## Additional Resources

- [Development Guide](./README.md) — Local setup
- [Database Migrations](./database-migrations.md) — Schema changes
- [Copilot Setup](./copilot-setup.md) — AI assistant testing
