# Implemented Enhancements

This document tracks features from the HARNESS_ENHANCEMENTS design that have been completed or partially implemented.

**Last Updated:** 2026-04-03

---

## Feature 0: Shared Frontend API Client

**Status:** ✅ Completed  
**Priority:** 0 | **Impact:** High | **Effort:** Small

### Implementation Summary

Created centralized API client at `frontend/lib/api.ts` to replace duplicated fetch logic across frontend pages.

### What Works

- **Typed DTOs:** Complete TypeScript interfaces for `Job`, `JobSource`, scan status, settings payloads
- **Base URL Handling:** Centralized via `NEXT_PUBLIC_API_URL` with fallback logic
- **Endpoint Coverage:** All existing routes wrapped with typed functions:
  - Jobs: `getJobs()`, `getJob()`, `getJobPdf()`, `applyToJob()`, `dismissJob()`
  - Sources: `getSources()`, `createSource()`, `updateSource()`, `deleteSource()`
  - Suggestions: `getSuggestions()`, `refreshSuggestions()`, `getScanStatus()`
  - Settings: `getGlobalFilter()`, `updateGlobalFilter()`
- **Consumer Integration:** Used by all frontend pages:
  - `app/suggestions/page.tsx`
  - `app/dashboard/page.tsx`
  - `app/jobs/[id]/page.tsx`
  - `app/apply/page.tsx`

### Expected Impact (Achieved)

- ✅ Unblocked implementation of Features 1, 4, 7, 8, 9, 11
- ✅ Eliminated duplicated endpoint logic across pages
- ✅ Single source of truth for API contracts

### Files Modified

- `frontend/lib/api.ts` (created)
- `frontend/app/suggestions/page.tsx` (refactored to use api.ts)
- `frontend/app/dashboard/page.tsx` (refactored to use api.ts)
- `frontend/app/jobs/[id]/page.tsx` (refactored to use api.ts)
- `frontend/app/apply/page.tsx` (refactored to use api.ts)

---

## Feature 3: Multi-Provider LLM Support

**Status:** 🟡 Partially Implemented  
**Priority:** 3 | **Impact:** High | **Effort:** Medium

### Implementation Summary

Abstracted LLM provider seam to support multiple AI providers (Gemini, Claude, OpenAI) with pluggable architecture.

### What's Implemented

#### ✅ Core Abstraction Layer

**File:** `backend/services/resume-tailor/core/llm_providers.py`

- **`LLMProvider` Abstract Base Class:**
  - `generate_text(prompt, temperature)` — text generation interface
  - `generate_content(prompt)` — backward-compatible alias with retry handling
  - `generate_structured(prompt, schema/response_schema)` — structured output with Pydantic validation
  - Flexible parameter handling: accepts either `schema=` or `response_schema=`

- **`GeminiProvider` (Production):**
  - Real runtime calls to Google Gemini API
  - Retry logic with exponential backoff
  - Token usage tracking via `response.usage_metadata`
  - Temperature and structured output support

- **`StubProvider` (Testing/Offline):**
  - Deterministic local mode for tests
  - Configurable mock responses
  - No external API calls

#### ✅ Agent Integration

**File:** `backend/services/resume-tailor/core/agents.py`

- All 4 agents refactored to accept `LLMProvider` abstraction:
  - `JobDiscoveryAgent(provider)`
  - `JobScoringAgent(provider)`
  - `JobParsingAgent(provider)`
  - `ResumeTailorAgent(provider)`
- Default provider created via `create_default_provider()` based on `RESUME_TAILOR_LLM_MODE` env var
- Consistent usage of `schema=` parameter and `generate_text()` calls

#### ✅ Runtime Configuration

**Environment Variable:** `RESUME_TAILOR_LLM_MODE`
- `real` (default) — Uses `GeminiProvider` with live API calls
- `stub` / `test` / `offline` — Uses `StubProvider` for local testing

### What's Pending

#### ❌ Additional Provider Implementations

- `ClaudeProvider` — Not yet implemented
  - Would use `anthropic` SDK
  - Requires `ANTHROPIC_API_KEY` configuration
- `OpenAIProvider` — Not yet implemented
  - Would use `openai` SDK
  - Requires `OPENAI_API_KEY` configuration

#### ❌ Model Registry

Not yet implemented:
```python
MODEL_REGISTRY = {
    "gemini-flash": {"provider": "gemini", "model_id": "gemini-2.0-flash-exp"},
    "gemini-pro":   {"provider": "gemini", "model_id": "gemini-1.5-pro"},
    "haiku":        {"provider": "claude", "model_id": "claude-haiku-4-5"},
    "sonnet":       {"provider": "claude", "model_id": "claude-sonnet-4-6"},
    "gpt-4o-mini":  {"provider": "openai", "model_id": "gpt-4o-mini"},
}
```

#### ❌ Per-Agent Model Selection

Not yet implemented:
- Settings table entries for model routing
- Environment variables like `DISCOVERY_AGENT_MODEL`, `SCORING_AGENT_MODEL`, etc.
- UI for model selection per agent type

#### ❌ Provider Failover

Not yet implemented:
- Automatic fallback chain when primary provider fails
- Multi-provider resilience strategy

#### ❌ Settings UI

Not yet implemented:
- `GET/PUT /settings/models` endpoints
- Frontend model selection interface
- Cost comparison display

### Verification Details

#### Resume Tailor Tests

**Command:**
```bash
cd backend/services/resume-tailor
/Users/alexyuan/Documents/job-auto-apply/.venv/bin/python -m unittest discover -s tests -v
```

**Result:** `Ran 10 tests in 0.000s — OK`

**Coverage:**
- ✅ `StubProvider` structured output validation
- ✅ Agent initialization with provider abstraction
- ✅ Backward compatibility for `generate_content()` alias
- ✅ `schema=` and `response_schema=` parameter flexibility

### Files Modified

- `backend/services/resume-tailor/core/llm_providers.py` (created)
- `backend/services/resume-tailor/core/agents.py` (refactored)
- `backend/services/resume-tailor/server.py` (uses provider factory)
- `backend/services/resume-tailor/tests/` (expanded with provider tests)

### Impact Achieved So Far

- ✅ Abstraction seam in place — adding new providers is now plug-and-play
- ✅ Testing mode available without API calls
- ✅ Foundation for TODO: "assign different agents to different models"

### Impact Still Pending

- ❌ Cross-vendor resilience (Gemini outage still = downtime)
- ❌ Cost optimization via cheap models for scoring
- ❌ Per-agent model tuning

---

## Feature 5: Site-Specific Scraper Plugins

**Status:** 🟡 Partially Implemented  
**Priority:** 5 | **Impact:** High | **Effort:** Large

### Implementation Summary

Created plugin architecture for site-specific scraper logic with domain-based routing and extensible extractor/resolver pattern.

### What's Implemented

#### ✅ Plugin Framework

**Files:** `backend/services/job-scraper/plugins/*/`

- **Plugin Manifest Schema:** JSON-based plugin configuration
- **Registry System:** Domain-based plugin selection at runtime
- **Fallback Plugin:** Generic extraction for unrecognized domains

#### ✅ Domain Plugin Packages

Implemented plugin packages for 6 company domains:

1. **`plugins/google/`** — Google Jobs / Google redirect handling
2. **`plugins/linkedin/`** — LinkedIn job postings
3. **`plugins/netflix/`** — Netflix careers (includes `jobs.netflix.com` and `netflex.com` typo-domain)
4. **`plugins/jane_street/`** — Jane Street careers
5. **`plugins/openai/`** — OpenAI careers (Greenhouse-based)
6. **`plugins/anthropic/`** — Anthropic careers

Each plugin includes:
- `manifest.json` — Domain patterns, plugin metadata
- `extractor.py` — Job listing extraction logic (currently delegates to generic)
- `resolver.py` — URL resolution logic (currently delegates to generic)

#### ✅ Tailor-Side URL Resolution

**File:** `backend/services/resume-tailor/core/site_plugins.py`

Extended `resolve_job_url()` with coverage for:
- ✅ Google redirect unwrapping (`/url?q=...` pattern)
- ✅ LinkedIn URL patterns
- ✅ Greenhouse / `boards.greenhouse.io` ATS
- ✅ Netflix (`jobs.netflix.com` + `netflex.com` typo support)
- ✅ Jane Street careers
- ✅ OpenAI careers (Greenhouse-based)
- ✅ Anthropic careers

#### ✅ Test Coverage

**Job Scraper Tests:**

**File:** `backend/services/job-scraper/tests/test_company_plugins.py` (new)

**Command:**
```bash
cd backend/services/job-scraper
/Users/alexyuan/Documents/job-auto-apply/.venv/bin/python -m unittest discover -s tests -v
```

**Result:** `Ran 13 tests in 0.735s — OK`

**Coverage:**
- ✅ Domain plugin selection for all 6 implemented sites
- ✅ Google redirect unwrapping behavior
- ✅ Company-specific resolver path handling
- ✅ Registry lookup and fallback logic

**Resume Tailor Tests:**

**File:** `backend/services/resume-tailor/tests/test_site_plugins.py` (expanded)

**Coverage:**
- ✅ Source URL resolution for all 6 sites
- ✅ Google redirect edge cases
- ✅ Relative-to-absolute URL resolution

### What's Pending

#### ❌ Site-Specialized Extractors

Current state:
- All new site plugins delegate extraction logic to generic fallback behavior
- This is **intentional for baseline reliability** but limits site-specific optimization

Not yet implemented:
- LinkedIn-specific selectors for job cards with anti-bot bypass
- Google Jobs dynamic URL rewrite handling
- ATS-specific (Greenhouse/Lever) structured data extraction
- Company portal pagination strategies

#### ❌ Plugin Error Telemetry

Not yet implemented:
- Per-plugin error tracking surfaced in `GET /suggestions/status`
- Rich plugin health reporting in frontend scan UX
- Plugin-specific retry/fallback strategies

#### ❌ Additional High-Value Sites

Not yet implemented:
- `lever` — Second most common ATS
- `workday` — Enterprise ATS
- `spotify` — Mentioned in TODOs
- `microsoft` — Mentioned in TODOs
- `uber` — Mentioned in TODOs

### Verification Details

All plugin routing tests pass with deterministic behavior. URL resolution correctly handles:
- Google redirect unwrapping: `/url?q=https://example.com/job` → `https://example.com/job`
- Domain pattern matching: Routes URLs to correct plugin based on manifest
- Fallback behavior: Unknown domains use generic plugin

### Files Created/Modified

**Created:**
- `backend/services/job-scraper/plugins/google/*`
- `backend/services/job-scraper/plugins/linkedin/*`
- `backend/services/job-scraper/plugins/netflix/*`
- `backend/services/job-scraper/plugins/jane_street/*`
- `backend/services/job-scraper/plugins/openai/*`
- `backend/services/job-scraper/plugins/anthropic/*`
- `backend/services/job-scraper/tests/test_company_plugins.py`

**Modified:**
- `backend/services/resume-tailor/core/site_plugins.py` (extended resolver coverage)
- `backend/services/resume-tailor/tests/test_site_plugins.py` (expanded coverage)
- `backend/services/job-scraper/tests/test_plugin_registry.py` (expanded)

### Impact Achieved So Far

- ✅ Plugin architecture in place for extensibility
- ✅ 6 company domains routable through plugin system
- ✅ Deterministic test coverage for routing and resolution
- ✅ Foundation for adding new sites without touching core code

### Impact Still Pending

- ❌ Site-specific extraction quality improvements
- ❌ ~30% URL resolution failures from unsupported sites
- ❌ Login-required sites (LinkedIn) still blocked
- ❌ TODO items for Netflix, Spotify, Microsoft Canada, Uber, Google still need specialized extractors

---

## Summary

| Feature | Status | What's Done | What's Pending |
|---------|--------|-------------|----------------|
| **0. Frontend API Client** | ✅ Complete | All endpoints wrapped, used by all pages | None |
| **3. Multi-Provider LLM** | 🟡 Partial | Provider abstraction, Gemini+Stub implementations, agent integration | Claude/OpenAI providers, model registry, per-agent selection, failover, settings UI |
| **5. Scraper Plugins** | 🟡 Partial | Plugin framework, 6 domain packages, routing, URL resolution, tests | Specialized extractors, error telemetry, additional sites (Lever, Workday, Spotify, Microsoft, Uber) |

---

## Next Steps

### To Complete Feature 3 (Multi-Provider LLM)
1. Implement `ClaudeProvider` using `anthropic` SDK
2. Implement `OpenAIProvider` using `openai` SDK
3. Create `MODEL_REGISTRY` with pricing data
4. Add per-agent model selection settings
5. Build provider failover chain
6. Add settings UI for model selection

### To Complete Feature 5 (Scraper Plugins)
1. Implement LinkedIn-specific extractor with login handling
2. Add Google Jobs dynamic URL rewrite logic
3. Create Greenhouse/Lever ATS specialized extractors
4. Add plugin error telemetry to `/suggestions/status`
5. Extend to Workday, Spotify, Microsoft, Uber plugins
6. Build plugin health reporting in frontend

---

_See [roadmap.md](./roadmap.md) for upcoming essential and very useful features._
