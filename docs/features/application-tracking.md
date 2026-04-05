# Application Tracking

## Overview

AutoCareer tracks each job across two layers:

1. **Workflow status** on `job.status` (`suggested`, `processing`, `active`, `rejected`, `dismissed`, `failed`)
2. **Interview stages** on `jobstage` (`applied`, `oa`, `interview`, `offer`) with timestamp + notes per stage

This supports non-linear progress (multiple stages can be completed at once) and preserves rejection context.

## Dashboard Behavior

### Visible Jobs

`/dashboard` shows jobs with status other than `suggested` and `dismissed`.

### Stage Progress UI

Each row shows a compact stage indicator:

- `✓` completed stage
- `⏳` next stage
- `○` not completed

Users can expand a row to edit:

- stage checkboxes (Applied/OA/Interview/Offer)
- stage notes
- rejection stage + rejection reason

All edits persist through `PUT /jobs/{id}/stages`.

## Status and Stage Semantics

### Status

- `suggested`: AI-discovered opportunity not yet started
- `processing`: background resume tailoring in progress
- `active`: in pipeline tracking (at least one completed stage, or active after rejection cleared)
- `rejected`: explicitly marked rejected with `rejection_stage`
- `dismissed`: hidden suggestion
- `failed`: processing error

### Stages

Tracked independently per job:

- `applied`
- `oa`
- `interview`
- `offer`

Each stage stores:

- `completed_at` (nullable timestamp)
- `notes` (nullable text)

## Rejection Tracking

Rejection is modeled on the job record:

- `rejection_stage`: one of `applied | oa | interview | offer`
- `rejection_reason`: free-form text

Behavior:

- setting `rejection_stage` marks status `rejected`
- sending `rejection_stage: null` clears rejection and returns job to `active`
- omitting `rejection_stage` preserves current rejection metadata

## API Surfaces Used by the UI

- `POST /apply`
  - starts processing
  - ensures initial `applied` stage exists (idempotent)
- `GET /jobs`
  - returns stage and rejection fields for each dashboard row
- `GET /jobs/{id}`
  - returns full job detail + stages
- `PUT /jobs/{id}/stages`
  - updates stage completion/notes and rejection metadata

## Troubleshooting

- If a job stays in `processing`, check backend logs (`docker-compose logs -f tailor`).
- If stage edits seem stale, refresh `/dashboard` and verify backend response in `GET /jobs/{id}`.
- If running hybrid DB mode, ensure both databases are on the same Alembic revision before sync.
