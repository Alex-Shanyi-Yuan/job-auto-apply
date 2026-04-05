# Top 3 Feature Refresh Design

**Date:** 2026-04-05  
**Scope:** Roadmap top 3 items not fully implemented:
1. Real-time streaming progress (SSE)
2. Pre/Post agent hooks for quality control
3. Bootstrap startup health checks

## Current State (Codebase Audit)

- `core/event_bus.py` exists with typed events and queue primitives.
- `process_application()` in `server.py` is still linear and does not emit stream events.
- No `GET /jobs/{job_id}/stream` endpoint exists in `server.py`.
- No `core/hooks.py` implementation exists.
- No `core/startup.py` health-check runner exists.
- Frontend job detail page (`frontend/app/jobs/[id]/page.tsx`) still shows static processing UI.
- Existing job stage/status functionality is active and should remain behaviorally stable.

## Design Goals

1. Implement top-3 roadmap features without regressing recent job stage/status work.
2. Keep modifications localized to apply/tailor flow and startup lifecycle.
3. Add verification coverage per slice to keep rollout safe.

## Architecture Boundary

- Keep the existing status/stage domain model and endpoints as system-of-record.
- Add an event sidecar for the apply pipeline:
  - `process_application()` emits typed events.
  - SSE endpoint streams those events for a job.
  - Hook runner wraps parse/tailor agent calls.
  - Startup checks run in lifespan and expose `/health`.
- Do not refactor suggestion scanning flow unless required for compatibility.

## Recommended Implementation Approach

Use **phased vertical slices** so each feature is usable and testable before moving on.

### Slice 1: SSE Progress (End-to-End)

- Backend:
  - Add `GET /jobs/{job_id}/stream`.
  - Add SSE generator with keepalive and completion close behavior.
  - Emit pipeline step events from `process_application()` (scrape/parse/tailor/compile/success/failure).
- Frontend:
  - Add `useJobStream` hook using `EventSource`.
  - Update job details processing UI to show live step state and concise progress indicators.
- Tests:
  - Unit test event serialization/queue behavior (extend existing event bus tests if needed).
  - API test for stream endpoint behavior on valid/invalid job IDs.

### Slice 2: Agent Hooks + Quality Gates

- Backend:
  - Create `core/hooks.py` with `HookResult`, `HookContext`, and `AgentHookRunner`.
  - Built-in hooks:
    - pre: master resume availability/shape
    - post: tailored latex validation (structure and markdown artifact checks)
    - post: optional warning hooks for observability
  - Integrate hooks into parse/tailor points in `process_application()`.
  - Preserve current failure semantics; when deny occurs, fail job and surface clear `error_message`.
- Retry behavior:
  - Keep existing `retry_count` schema usage compatible with current status flow.
  - Add controlled retries only in tailor/hook-failure path if configuration enables it.
- Tests:
  - Hook unit tests (allow/warn/deny behavior).
  - Pipeline tests covering hook denial -> failed status path.

### Slice 3: Startup Health Checks

- Backend:
  - Create `core/startup.py` with ordered checks:
    - database connectivity
    - migration baseline
    - master resume presence
    - Gemini API key configured
    - scraper reachability
    - `pdflatex` availability
  - Integrate runner in FastAPI lifespan.
  - Add `GET /health` response with per-check results.
  - Critical-check failure should stop serving apply-related flows according to configured fail-fast mode.
- Frontend:
  - Optional lightweight warning banner integration deferred unless required by acceptance criteria.
- Tests:
  - Health check unit tests with mocked pass/fail paths.
  - Lifespan startup behavior tests for critical failure mode.

## Error Handling and Compatibility

- No silent failures: emit explicit events and persist actionable error messages on jobs.
- Maintain current stage/status API contract and avoid changing enum semantics.
- Keep changes additive where possible (new modules, new endpoint, guarded integration points).

## Verification Strategy

- Run backend tests and frontend lint/test/build commands already present in repo.
- Add focused tests for each slice; then run full regression on job stage/status tests.
- Validate SSE and `/health` behavior manually in local compose flow after automated checks.

## Out of Scope

- Audit log persistence feature.
- Token-cost dashboard feature.
- Broad refactor of existing status stage flows.
