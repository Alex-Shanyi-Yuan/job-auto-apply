# Resume Tailor API

Base URL (local): `http://localhost:8000`

## Jobs

| Method | Path | Description |
|---|---|---|
| `POST` | `/apply` | Start tailoring workflow for a job URL. Ensures initial `applied` stage exists. |
| `GET` | `/jobs` | List non-suggested, non-dismissed jobs including stage/rejection fields. |
| `GET` | `/jobs/{id}` | Get a single job with full stage detail. |
| `PUT` | `/jobs/{id}/stages` | Update stage completion/notes and rejection metadata. |
| `GET` | `/jobs/{id}/pdf` | Download generated resume PDF. |
| `POST` | `/jobs/{id}/dismiss` | Dismiss suggested job. |

## Sources

| Method | Path | Description |
|---|---|---|
| `GET` | `/sources` | List job sources. |
| `POST` | `/sources` | Create job source. |
| `PUT` | `/sources/{id}` | Update job source. |
| `DELETE` | `/sources/{id}` | Delete job source. |

## Suggestions

| Method | Path | Description |
|---|---|---|
| `GET` | `/suggestions` | List suggested jobs ordered by score. |
| `POST` | `/suggestions/refresh` | Trigger discovery scan. Optional `source_ids`. |
| `GET` | `/suggestions/status` | Scan progress and per-source report. |

## Settings

| Method | Path | Description |
|---|---|---|
| `GET` | `/settings/global-filter` | Read global discovery filter. |
| `PUT` | `/settings/global-filter` | Update global discovery filter. |

---

## Stage Tracking Request/Response

### `PUT /jobs/{id}/stages` Request

```json
{
  "stages": [
    { "name": "applied", "completed": true, "notes": "Applied via careers page" },
    { "name": "oa", "completed": true, "notes": "Completed HackerRank" },
    { "name": "interview", "completed": false },
    { "name": "offer", "completed": false }
  ],
  "rejection_stage": null,
  "rejection_reason": null
}
```

### Response (abridged)

```json
{
  "id": 123,
  "status": "active",
  "stages": [
    {
      "stage_name": "applied",
      "completed_at": "2026-04-05T00:12:00",
      "notes": "Applied via careers page"
    },
    {
      "stage_name": "oa",
      "completed_at": "2026-04-08T16:45:00",
      "notes": "Completed HackerRank"
    }
  ],
  "rejection_stage": null,
  "rejection_reason": null,
  "created_at": "2026-04-05T00:12:00",
  "updated_at": "2026-04-08T16:45:00"
}
```

---

## Data Model Notes

### `job` (core fields)

- `status`: `suggested | processing | active | rejected | dismissed | failed`
- `rejection_stage`: nullable `applied | oa | interview | offer`
- `rejection_reason`: nullable text

### `jobstage`

- `job_id` (FK → `job.id`)
- `stage_name` (`applied | oa | interview | offer`)
- `completed_at` (nullable datetime)
- `notes` (nullable text)
- unique constraint on `(job_id, stage_name)`

---

## Behavior Details

- `POST /apply` is idempotent for initial stage creation (`applied` stage won’t duplicate).
- In `PUT /jobs/{id}/stages`:
  - setting `rejection_stage` sets status `rejected`
  - explicitly sending `rejection_stage: null` clears rejection metadata and returns status `active`
  - omitting `rejection_stage` preserves existing rejection metadata
- Completed stages are returned ordered by `completed_at`.
