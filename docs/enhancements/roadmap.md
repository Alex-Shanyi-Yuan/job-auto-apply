# Enhancement Roadmap

This document outlines the prioritized enhancement features for AutoCareer, extracted from the full HARNESS_ENHANCEMENTS.md design document. Features are organized by priority tier.

---

## Essential Features (Must Have)

These features are critical for system reliability and core user experience.

### 1. Real-Time Streaming Progress via Server-Sent Events

**Priority:** 1 | **Impact:** High | **Effort:** Medium

**Problem Statement:**

The frontend has no real-time visibility into long-running resume tailoring operations (~10–30 seconds). The `jobs/[id]/page.tsx` page fetches job status once on mount but provides no step-by-step progress updates. Backend processing runs in background tasks with thread offload, but there is no push channel for intermediate pipeline state. Users see a static "Processing..." state with no indication of where the pipeline is or if it's stalled.

**What to Build:**

- **Backend:** Add `GET /jobs/{job_id}/stream` SSE endpoint that emits pipeline step events as background tasks progress
- **Event Bus:** Create per-job `asyncio.Queue` for publishing events (`scraping_complete`, `parsing_complete`, `tailoring_started`, `tailoring_complete`, `pdf_compiled`, `failed`)
- **Instrumentation:** Inject event emission calls into `process_application()` at each major step
- **Frontend:** Add `EventSource` connection on `jobs/[id]/page.tsx` to receive and display real-time progress
- **UI:** Display user-friendly labels ("Analyzing job requirements...", "Rewriting resume bullet points...", "Compiling PDF...")

**Expected Impact:**

- Eliminates user uncertainty during resume tailoring flow
- Makes 10-30 second processing feel responsive (users see first step in <1s)
- Replaces static waiting with live progress events
- Unblocks user trust in the apply button — they know exactly where the pipeline is

---

### 2. Pre/Post Agent Hooks for Quality Control

**Priority:** 2 | **Impact:** High | **Effort:** Medium

**Problem Statement:**

The 4 AI agents (`agents.py`) execute with no validation layer between prompt and output. LaTeX validation only checks for 3 basic structure strings (`\documentclass`, `\begin{document}`, `\end{document}`). When the LLM hallucinates broken LaTeX (unclosed braces, markdown fences in LaTeX output), PDF compilation fails and the job lands in `status="failed"` with a cryptic error message. There is no monitoring, logging, or quality gate mechanism without directly modifying agent implementation code.

**What to Build:**

- **Hook System:** Create `core/hooks.py` with `AgentHookRunner` that supports pre-call and post-call validation hooks
- **Hook Interface:** Python callables with signature `(agent_name, input_data) -> HookResult` returning `ALLOW | DENY | WARN`
- **Built-in Hooks:**
  - Pre-hook: `validate_resume_latex_input` — verify master.tex loads without syntax errors
  - Post-hook: `validate_tailored_latex` — detect common LLM LaTeX mistakes (unclosed braces, markdown artifacts)
  - Post-hook: `log_agent_output` — structured logging for debugging
  - Post-hook: `warn_on_low_score` — surface JobScoringAgent scores < 30
- **Agent Integration:** Wrap all agent calls in `process_application()` with hook execution
- **Quality Gates:** Deny pipeline continuation if post-hook validation fails

**Expected Impact:**

- Reduces `status="failed"` jobs caused by bad LaTeX (currently the #1 failure mode)
- Adds observability to every agent call without reading raw logs
- Provides extension point for custom validation without touching agent code
- Addresses TODO: "resume tailor logic make it based on json experience based structure" via hook validation

---

### 9. Bootstrap Sequence and Startup Health Checks

**Priority:** 9 | **Impact:** Medium | **Effort:** Small

**Problem Statement:**

`server.py` startup creates database tables and runs migrations silently with no health verification. Critical failures only surface at runtime:
- Missing Gemini API key → server starts fine but all agent calls fail with `401 Unauthorized`
- Missing `pdflatex` binary → server starts but PDF compilation fails on first apply
- Database connection issues → silent failure until first query
- Scraper service unreachable → no warning until scrape attempt

Users have no visibility into what dependencies are ready or misconfigured.

**What to Build:**

- **Startup Phases:** Create `core/startup.py` with ordered health check phases:
  - `database_connection` — verify DB is reachable
  - `migrations_applied` — ensure schema is current
  - `master_resume_exists` — validate resume template file
  - `gemini_api_key` — check API credentials are configured
  - `scraper_reachable` — ping scraper service health
  - `pdflatex_available` — verify LaTeX toolchain
- **Health Endpoint:** Add `GET /health` that returns startup check results
- **Fast-Fail:** If critical config missing (e.g., `GOOGLE_API_KEY`), disable agent endpoints with `503 Service Unavailable` and descriptive error
- **Frontend Integration:** Call `/health` on app load, show warning banner for any unavailable services

**Expected Impact:**

- Eliminates "why is everything broken?" debugging on fresh install
- Surfaces `pdflatex` missing immediately instead of on first apply (the #2 reported setup issue)
- Provides operators with `/health` endpoint for container health probes
- Gives users clear feedback about what's misconfigured

---

### 11. Timezone-Aware Date Handling

**Priority:** 11 | **Impact:** Low | **Effort:** Small

**Problem Statement:**

The `isToday()` function in `dashboard/page.tsx` compares dates in local browser timezone, but `Job.created_at` is stored as UTC by PostgreSQL. This creates display bugs:
- A job created at 11:31 PM UTC appears as "Tomorrow" for a user in UTC-4 (7:31 PM local)
- The "Today" view incorrectly splits jobs across date boundaries
- Users see inconsistent grouping based on their timezone offset

Addresses TODO: "timezone issue pass 7:31 pm counted as the next day?"

**What to Build:**

- **Backend:** Return `created_at` timestamps as ISO 8601 with timezone offset (e.g., `2025-04-02T19:31:00-04:00`)
- **Frontend Fix:** Update `isToday()` to compare dates in UTC by normalizing both sides
- **Server Time Endpoint:** Add `GET /settings/server-time` to provide server's current time as reference
- **Display Standardization:** Use `Intl.DateTimeFormat` with `timeZoneName: "short"` for all timestamp displays

**Expected Impact:**

- Fixes date grouping bugs in dashboard
- Small change with high correctness improvement
- Stops jobs from appearing in wrong day groups

---

## Very Useful Features (Should Have Soon)

These features significantly improve observability, safety, and cost management.

### 4. Token Usage Tracking and Cost Dashboard

**Priority:** 4 | **Impact:** Medium | **Effort:** Small

**Problem Statement:**

There is no tracking of LLM token consumption per job or per scan. Users have no visibility into API costs. Each Gemini call returns usage metadata (`response.usage_metadata.prompt_token_count`, `response.usage_metadata.candidates_token_count`) that is currently discarded. With 100+ jobs scored per scan, API costs can accumulate unexpectedly. Users cannot make informed decisions about model selection or source configuration without cost data.

**What to Build:**

- **Token Capture:** Update `llm_client.py` to extract and return `TokenUsage` dataclass alongside content
- **Database Schema:** Add migration to include `input_tokens`, `output_tokens`, `estimated_cost_usd` columns on `Job` table
- **Cost Calculation:** Implement pricing lookup table mapping models to per-million-token costs
- **Accumulation:** Track token usage across all 3 agent calls in `process_application()` and save totals
- **Dashboard Display:** Add cost column to jobs table in `dashboard/page.tsx`
- **Scan Reports:** Include scan-level cost summary in suggestions page scan report modal

**Expected Impact:**

- Surfaces real API spend so users can tune model choices (connects to Feature 3: multi-provider)
- Enables cost-per-application metric ("this resume tailoring cost $0.04")
- Enables per-scan cost visibility ("found 47 jobs, scored 23, cost $0.12 total")
- No architecture change needed — Gemini already returns usage metadata

---

### 7. Conversation/Audit Logging per Job Application

**Priority:** 7 | **Impact:** Medium | **Effort:** Small

**Problem Statement:**

When `status="failed"`, only `str(exception)` is saved to `Job.error_message`. When resume tailoring produces poor results, there is no way to see:
- What prompts were sent to the LLM
- What the LLM responded with
- Why the scoring agent gave a particular score
- Which pipeline step caused a failure

Debugging requires re-running the entire pipeline. Quality review of tailored resumes is impossible without manual inspection of compiled PDFs.

**What to Build:**

- **Audit Schema:** Add `audit_log` JSON column to `Job` table storing array of pipeline step records
- **Audit Entry Model:** Create `AuditEntry` dataclass capturing:
  - `step` (scraping/parsing/tailoring/compiling)
  - `timestamp`, `duration_ms`
  - `input_preview` (first 200 chars), `output_preview` (first 200 chars)
  - `input_tokens`, `output_tokens`
  - `error` (if step failed)
- **Collection:** Wrap each agent call in `process_application()` with timing and data capture
- **Persistence:** Save audit log regardless of pipeline success/failure
- **API:** Add `GET /jobs/{job_id}/audit` endpoint
- **UI:** Add expandable "Pipeline Log" section in `jobs/[id]/page.tsx` showing step-by-step execution

**Expected Impact:**

- Changes debugging from "why is status=failed?" to "here's exactly what broke and where"
- Enables quality review: inspect tailored LaTeX before compiling
- Reduces failed jobs by catching LLM issues early (feeds back into Feature 2: hooks)
- Small database cost: ~2–5KB JSON per job

---

### 8. Dry-Run / Safe-Scan Permission Mode

**Priority:** 8 | **Impact:** Medium | **Effort:** Small

**Problem Statement:**

`POST /apply` immediately starts the full pipeline including expensive LLM calls and PDF compilation. There is no way to:
- Test discovery/scoring flow without committing API spend
- Preview what the scraper extracted before tailoring
- Validate a new source configuration without live LLM calls
- Review detected company/title before applying

Users must commit resources before seeing if the operation will succeed.

**What to Build:**

- **API Parameter:** Add `dry_run: bool = False` query parameter to:
  - `POST /apply?dry_run=true` — fetch and parse job but skip tailoring/PDF, return preview
  - `POST /suggestions/refresh?dry_run=true` — scrape sources, return discovered jobs without scoring or saving
- **Implementation:** In `server.py`, branch logic based on dry_run flag to skip LLM calls and DB writes
- **Preview Mode:** Return detected job metadata (company, title, requirements) without persistence
- **UI Integration:**
  - Add "Preview" button to `apply/page.tsx` 
  - Add scan preview mode to suggestions page
- **Settings:** Store dry_run preference in `Settings` table for default behavior

**Expected Impact:**

- Reduces wasted API spend on malformed URLs or pages scraper can't handle
- Lets users confirm job detection works before burning API credits
- Provides safety net for new source configurations
- Enables testing and validation workflows

---

## Build Recommendations

### Phase 1: Reliability Foundation
**Features:** 9 → 11 → 2  
Start with startup health checks and timezone fix (both small, high trust impact), then add hooks to catch LaTeX failures.

### Phase 2: Observability
**Features:** 4 → 7 → 1  
Track costs and add audit logging before building streaming UI — you need the per-step data to power stream events.

### Phase 3: Safety & Validation
**Features:** 8  
Add dry-run mode for safe testing and cost control.

---

## Notes

- See [implemented.md](./implemented.md) for features already completed or partially implemented
- See [archive/harness-inspiration.md](./archive/harness-inspiration.md) for the complete original design document with all 11 features
- Cross-reference with project TODOs in `/TODO.todo` for related work items
