# Design Doc: Site-Specific Scraper Plugin System

## 1. Document Purpose

This document explains, from first principles, how AutoCareer currently finds jobs, where it fails, and how to implement a site-specific scraper plugin system that improves reliability and scalability.

Audience:

- Engineers new to the project
- Contributors implementing scraper improvements
- Maintainers evaluating impact and rollout risk

---

## 2. Project Overview (For New Contributors)

AutoCareer is a self-hosted job application automation platform with four services:

- `frontend` (Next.js): user interface for scanning jobs, reviewing suggestions, and generating tailored resumes.
- `tailor` (FastAPI): main API service that orchestrates job discovery, scoring, parsing, and resume tailoring.
- `scraper` (FastAPI + Playwright): fetches and cleans web pages.
- `postgres`: stores jobs, sources, and settings.

High-level workflow:

1. User configures job source URLs in the frontend.
2. `tailor` triggers a scan and calls `scraper` to fetch source pages.
3. AI extracts job cards from source HTML.
4. AI scores jobs and stores them as suggestions.
5. User applies to a job, then `tailor` generates a tailored resume PDF.

---

## 3. Current State

### 3.1 Current Discovery Pipeline

Today, discovery runs in `backend/services/resume-tailor/server.py` in `process_job_discovery()` and `process_single_source()`.

Per source:

1. Scrape source page (`POST /scrape` with `format="html"`).
2. Use `JobDiscoveryAgent` to extract jobs from HTML.
3. Resolve each extracted URL using one generic resolver (`resolve_job_url`).
4. For each new job, scrape job page and score it.
5. Save jobs to database and return scan status.

### 3.2 Current Scraper Behavior

`backend/services/job-scraper/main.py` exposes one generic `POST /scrape` endpoint.

Behavior is currently uniform for all sites:

- Launch Playwright
- Open URL
- Wait a fixed amount of time
- Scroll once
- Return cleaned HTML or plain text

### 3.3 Why This Fails in Practice

Job sites are structurally different:

- Some are server-rendered and simple.
- Some are JS-heavy and need custom waiting/selectors.
- Some use redirects or wrapped links that need custom URL recovery.
- Some rate-limit or block generic browser patterns.

One generic strategy cannot reliably handle all of them.

---

## 4. Problem Statement

Current bottlenecks:

1. Generic scraping strategy across heterogeneous sites causes discovery loss.
2. Generic URL resolution fails for site-specific link patterns.
3. Failures are hard to diagnose because error context is coarse.
4. Supporting a new site requires editing core logic, increasing regression risk.

Business impact:

- Fewer suggested jobs discovered
- More hidden failures (jobs found but not actually scorable)
- Slower support for high-value sites

Engineering impact:

- Accumulating conditional logic in shared code
- Harder testing and troubleshooting
- Poor separation of concerns

---

## 5. Goal and Non-Goals

### 5.1 Goals

1. Introduce a plugin architecture that routes scraping/resolution behavior by site.
2. Keep backward compatibility using a generic fallback plugin.
3. Improve discovery-to-scoring success rate on high-priority sites.
4. Surface plugin and error details in scan status.
5. Make adding a new site mostly additive (new plugin files).

### 5.2 Non-Goals (Initial Version)

1. No account-based authenticated scraping flow (for example persistent login/cookies) in v1.
2. No full rewrite of the AI discovery/scoring pipeline.
3. No immediate database schema expansion unless needed for reporting.

---

## 6. Proposed Design

### 6.1 Plugin Concept

Each job site gets a plugin package with:

- `manifest` (metadata and matching rules)
- `extractor` (site-specific listing extraction hints/logic)
- `resolver` (site-specific URL normalization)

The scraper chooses a plugin by domain (or URL pattern). If no match exists, it uses the generic plugin.

### 6.2 Proposed Directory Structure

```text
backend/services/job-scraper/
  plugins/
    plugin_schema.py
    plugin_registry.py
    generic/
      plugin.json
      extractor.py
      resolver.py
    linkedin/
      plugin.json
      extractor.py
      resolver.py
    google_jobs/
      plugin.json
      extractor.py
      resolver.py
    greenhouse/
      plugin.json
      extractor.py
      resolver.py
```

### 6.3 Manifest Shape (Example)

```json
{
  "name": "linkedin",
  "version": "1.0.0",
  "domains": ["linkedin.com", "www.linkedin.com"],
  "wait_selector": ".job-card-container",
  "pagination_strategy": "none",
  "extractor": "extractor.py",
  "resolver": "resolver.py"
}
```

### 6.4 Service Integration

1. `scraper` startup loads plugin manifests into registry.
2. On `/scrape`, scraper resolves plugin by URL and applies plugin-specific behavior.
3. `tailor` URL resolution delegates to plugin resolver instead of one generic function.
4. `scan_status` and per-source result include plugin metadata and categorized failure reasons.

---

## 7. Architecture and Data Flow

### 7.1 Before

```text
source URL -> generic scrape -> AI discovery -> generic URL resolve -> scrape job -> score -> save
```

### 7.2 After

```text
source URL -> plugin match -> plugin scrape/extract -> AI discovery -> plugin URL resolve -> scrape job -> score -> save
                                  |                                |
                                  +---- plugin identity -----------+
                                          included in scan report
```

---

## 8. Execution Plan (Detailed)

## Phase 0: Baseline and Guardrails

Objective:

- Capture baseline metrics before changing behavior.

Tasks:

1. Record current scan success on representative sources.
2. Save current discovered jobs count, scored jobs count, and source-level failures.
3. Freeze a test source list for repeatable comparisons.

Exit criteria:

- Baseline report exists and is committed as reference document.

## Phase 1: Plugin Infrastructure

Objective:

- Add scaffolding with zero behavior change.

Tasks:

1. Add `plugin_schema.py` with validation for manifest fields.
2. Add `plugin_registry.py` to load plugins and match domain to plugin.
3. Add generic plugin package implementing current behavior.
4. Add startup logging: loaded plugin count, skipped invalid manifests.

Exit criteria:

- Service starts with registry loaded.
- All URLs route through generic plugin if no site plugin exists.
- Existing scans remain functional.

## Phase 2: Migrate Existing Generic Logic

Objective:

- Move current hardcoded logic into generic plugin modules.

Tasks:

1. Move HTML cleaning/extraction helpers into `plugins/generic/extractor.py`.
2. Move URL resolution behavior into `plugins/generic/resolver.py`.
3. Update `tailor` service to call plugin resolver API.
4. Keep old behavior behind temporary compatibility path for rollback.

Exit criteria:

- Output parity with baseline on same sources.
- No user-visible behavior change.

## Phase 3: Implement High-Impact Site Plugins

Objective:

- Improve outcomes for known problematic sources.

Target plugins:

1. LinkedIn
2. Google Jobs
3. Greenhouse

Tasks per plugin:

1. Create manifest with domain rules.
2. Implement extractor hints/transform.
3. Implement resolver for site-specific URL normalization.
4. Add fixture-based tests (HTML sample -> expected listings and URL forms).

Exit criteria:

- Plugin-specific tests pass.
- End-to-end scans show improvement for each target site.

## Phase 4: Observability and UX

Objective:

- Make plugin behavior and failures visible.

Backend tasks:

1. Extend source scan result payload with:
   - `plugin_name`
   - `scrape_failures`
   - `failure_reason` category (`timeout`, `site_blocking`, `plugin_error`, `scrape_error`)
2. Add error classification in source processing pipeline.

Frontend tasks:

1. Show plugin used per source in scan report.
2. Show categorized failure reason and count.
3. Keep existing added/skipped job report UX unchanged.

Exit criteria:

- Operators can identify site-specific failure causes from UI.

## Phase 5: Rollout and Hardening

Objective:

- Deploy safely and keep rollback simple.

Tasks:

1. Add feature flag to disable plugin routing and revert to generic behavior.
2. Canary rollout on selected sources first.
3. Compare canary metrics against baseline.
4. Publish plugin authoring guide for future site additions.

Exit criteria:

- Production rollout complete with no critical regressions.

---

## 9. Testing Strategy

### 9.1 Unit Tests

1. Manifest validation and loader errors.
2. Domain matching and fallback behavior.
3. URL resolver correctness per plugin.

### 9.2 Integration Tests

1. Source scan path with plugin selected.
2. Job page scrape and score path still works.
3. Error classification path returns expected categories.

### 9.3 E2E Validation

1. Run the same source set before and after plugin rollout.
2. Validate frontend scan report shows plugin and reason fields.
3. Confirm no regression for non-plugin sites.

---

## 10. Metrics and Success Criteria

Primary success metrics:

1. Discovery-to-scoring conversion rate increases for target sites.
2. Source-level scrape failure rate decreases on plugin sites.
3. Time to add support for a new site decreases significantly.

Operational metrics:

1. Plugin load failures at startup.
2. Scrape timeout rate by plugin.
3. Failure reason distribution by source.

Quality bar:

- Improvement must be measurable against Phase 0 baseline.

---

## 11. Risks and Mitigations

Risk: Site markup changes break a plugin.
Mitigation: Keep generic fallback, add fixture tests, monitor failure reason spikes.

Risk: Plugin bug affects all scans.
Mitigation: Feature flag, canary rollout, startup validation that skips invalid plugins.

Risk: Complexity increases maintenance cost.
Mitigation: Strict plugin contract, template plugin, plugin authoring guide.

Risk: Some sites require auth/session to scrape reliably.
Mitigation: Explicitly mark as out-of-scope for v1 and track as follow-up.

---

## 12. Rollout Timeline (Example)

- Week 1: Phase 0 + Phase 1
- Week 2: Phase 2
- Week 3-4: Phase 3 (parallel plugin implementation)
- Week 5: Phase 4
- Week 6: Phase 5 and production rollout

---

## 13. Expected Project Impact

User impact:

- More relevant suggestions discovered reliably.
- Fewer silent failures during scans.
- Better transparency on why specific sources underperform.

Engineering impact:

- Cleaner architecture and reduced core code churn.
- Faster onboarding of new site support.
- Better failure observability and targeted debugging.

Product impact:

- Higher throughput from discovery to application.
- Improved trust in scan results.
- Better scalability for future source expansion.

---

## 14. Open Questions

1. Should plugin metadata be persisted in database for historical analytics?
2. Should plugin routing live only in scraper, or also in tailor for URL resolution parity?
3. Which sources should be in initial canary set?
4. Do we want a dedicated plugin health endpoint for operations dashboards?

---

## 15. Immediate Next Actions

1. Approve this design doc.
2. Create implementation tickets from Phases 0-5.
3. Start Phase 0 baseline capture.
4. Begin Phase 1 scaffold with generic fallback plugin.
