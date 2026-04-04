# Job Application Stage Tracking - Design Specification

**Created:** 2024-04-04  
**Status:** Approved  
**Feature:** Track interview pipeline stages (Applied, OA, Interview, Offer) with timestamps for statistics and analytics

---

## Problem Statement

Currently, AutoCareer tracks jobs with a single `status` field that represents a linear progression (suggested → applied → interviewing → offer). This limits visibility into the interview pipeline and prevents generating useful statistics like:
- Conversion rates at each stage (Applied → OA → Interview → Offer)
- Average time between stages
- Which companies/roles have the best conversion rates
- Where rejections typically occur

Users need to track multiple stages simultaneously with timestamps to understand their job search funnel and optimize their strategy.

---

## Requirements

### Functional Requirements
1. Track 4 distinct stages: **Applied**, **OA** (Online Assessment), **Interview**, **Offer**
2. Each stage has:
   - Boolean completion status (checked/unchecked)
   - Timestamp when completed (nullable)
   - Optional user notes (free text)
3. Stages can be completed in any order (non-linear)
4. Multiple stages can be checked simultaneously
5. Track rejection separately:
   - Which stage rejection occurred at
   - Free-form rejection reason/notes
6. Maintain backward compatibility with existing job data
7. Support hybrid database mode (SQLite ↔ PostgreSQL sync)

### Non-Functional Requirements
- Clean, modern UI that doesn't clutter the dashboard
- Fast API responses (< 200ms for stage updates)
- Schema migrations must be idempotent and safe for hybrid mode
- No data loss during migration from old status model

---

## Design Overview

### Architecture Approach: Separate Stages Table

**Chosen:** Option 1 - Create a dedicated `JobStage` table (one row per stage per job)

**Rationale:**
- ✅ Clean separation of concerns (job metadata vs. stage progression)
- ✅ Easy to query statistics ("show all OA completion times")
- ✅ Flexible for future enhancements (add more stages, track metadata per stage)
- ✅ Maintains audit trail (can track stage history if needed later)
- ✅ Works well in both SQLite and PostgreSQL

**Rejected Alternatives:**
- JSON column: Poor query performance, limited SQLite JSON support, harder to generate analytics
- Boolean columns: Schema changes for each new stage, less flexible long-term

---

## Database Schema

### New Table: `JobStage`

```python
class JobStage(SQLModel, table=True):
    """Tracks individual stages in the interview pipeline for a job."""
    id: Optional[int] = Field(default=None, primary_key=True)
    job_id: int = Field(foreign_key="job.id", ondelete="CASCADE")
    stage_name: str  # 'applied' | 'oa' | 'interview' | 'offer'
    completed_at: Optional[datetime] = None  # When stage was completed
    notes: Optional[str] = None  # User notes for this stage
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    
    __table_args__ = (
        UniqueConstraint('job_id', 'stage_name', name='uq_job_stage'),
    )
```

**Indexes:**
- Primary key on `id`
- Unique constraint on `(job_id, stage_name)` - one record per stage per job
- Foreign key index on `job_id` (automatic)

### Job Table Modifications

**New Columns:**
```python
class Job(SQLModel, table=True):
    # ... existing columns ...
    
    # New fields for rejection tracking
    rejection_stage: Optional[str] = None  # 'applied' | 'oa' | 'interview' | 'offer'
    rejection_reason: Optional[str] = None  # Free-form rejection notes
```

**Modified Column:**
```python
# Simplified status values
status: str = "suggested"  
# Values: 'suggested' | 'active' | 'rejected' | 'dismissed' | 'failed'
```

**Status Field Semantics:**
- `suggested`: Discovered by AI, not yet applied
- `active`: User has applied, tracking stages
- `rejected`: User marked as rejected (see rejection_stage for details)
- `dismissed`: User dismissed the suggestion
- `failed`: System error during processing (keep for debugging)

---

## Data Migration Strategy

### Migration File: `005_add_job_stage_tracking.py`

**Upgrade Logic:**
1. Create `jobstage` table
2. Add `rejection_stage` and `rejection_reason` columns to `job` table
3. Migrate existing data:
   ```python
   # For jobs with status='applied'
   → Create JobStage(job_id=X, stage_name='applied', completed_at=job.created_at)
   → Update job.status = 'active'
   
   # For jobs with status='interviewing'
   → Create JobStage(stage_name='applied', completed_at=job.created_at)
   → Create JobStage(stage_name='interview', completed_at=job.created_at)
   → Update job.status = 'active'
   
   # For jobs with status='offer'
   → Create JobStage for all 4 stages with completed_at=job.created_at
   → Update job.status = 'active'
   
   # Keep status='rejected', 'dismissed', 'failed', 'suggested' unchanged
   ```
4. Migration is idempotent (safe to run multiple times)

**Downgrade Logic:**
- Drop `rejection_stage` and `rejection_reason` columns
- Drop `jobstage` table
- Revert `status` values to old schema (best effort)

### Hybrid Mode Schema Sync

**Challenge:** SQLite and PostgreSQL must have identical schemas for sync to work.

**Solution:**
1. **Bootup Sequence:**
   - `entrypoint.sh` runs `alembic upgrade head` on active database
   - If `DATABASE_BACKEND=hybrid`: migrations run on SQLite first
   - Before enabling sync: check Alembic version on both databases
   - If versions differ: attempt migration on lagging DB
   - If migration fails: disable sync, log error, continue with active DB only

2. **Schema Version Check:**
   ```python
   # In core/db_sync.py
   def check_schema_parity():
       sqlite_version = get_alembic_version(sqlite_engine)
       postgres_version = get_alembic_version(postgres_engine)
       return sqlite_version == postgres_version
   ```

3. **Fallback Behavior:**
   - PostgreSQL unreachable → SQLite continues normally
   - Schema mismatch → Disable sync, log warning to stderr
   - User can manually run `alembic upgrade head` in both environments

---

## API Specification

### New Endpoints

#### `PUT /jobs/{job_id}/stages`
Update stage progression for a job.

**Request:**
```json
{
  "stages": [
    {
      "name": "applied",
      "completed": true,
      "notes": "Applied via company website"
    },
    {
      "name": "oa",
      "completed": true,
      "notes": "Completed HackerRank assessment"
    },
    {
      "name": "interview",
      "completed": false
    },
    {
      "name": "offer",
      "completed": false
    }
  ],
  "rejection_stage": null,
  "rejection_reason": null
}
```

**Response:**
```json
{
  "id": 123,
  "title": "Software Engineer",
  "company": "Google",
  "status": "active",
  "stages": [
    {
      "stage_name": "applied",
      "completed_at": "2024-01-15T10:00:00Z",
      "notes": "Applied via company website"
    },
    {
      "stage_name": "oa",
      "completed_at": "2024-01-20T14:30:00Z",
      "notes": "Completed HackerRank assessment"
    }
  ],
  "rejection_stage": null,
  "rejection_reason": null,
  "created_at": "2024-01-15T10:00:00Z"
}
```

**Business Logic:**
- If stage `completed: true` and no existing `JobStage` record → create with `completed_at = now()`
- If stage `completed: true` and existing record has `completed_at = null` → set `completed_at = now()`
- If stage `completed: false` and existing record → set `completed_at = null`
- Update `job.status = 'active'` if any stage is completed
- Update `job.rejection_stage` and `job.rejection_reason` if provided

### Modified Endpoints

#### `GET /jobs/{job_id}`
**Changes:** Include `stages` array in response

**Response:**
```json
{
  "id": 123,
  "url": "https://...",
  "company": "Google",
  "title": "Software Engineer",
  "status": "active",
  "score": 95,
  "stages": [
    {"stage_name": "applied", "completed_at": "2024-01-15T10:00:00Z", "notes": "..."},
    {"stage_name": "oa", "completed_at": "2024-01-20T14:30:00Z", "notes": "..."}
  ],
  "rejection_stage": null,
  "rejection_reason": null,
  "created_at": "2024-01-15T10:00:00Z"
}
```

#### `GET /jobs`
**Changes:** Include `stages` array for each job (LEFT JOIN query)

#### `POST /apply`
**Changes:** After successful application, create initial `JobStage`:
```python
job_stage = JobStage(
    job_id=job.id,
    stage_name="applied",
    completed_at=utcnow()
)
session.add(job_stage)
job.status = "active"
```

---

## Frontend UI Design

### Dashboard Enhancement: Expandable Rows

**Goal:** Show stage progress without cluttering the table, with clean modern design.

**Approach:** Inline expandable rows (no modals)

#### Collapsed View (Default)
```
┌────────────────────────────────────────────────────────────────────┐
│ Company  │ Title          │ Progress         │ Score │ Date       │
├────────────────────────────────────────────────────────────────────┤
│ Google ▶ │ SWE            │ ✓ → ✓ → ⏳ → ○   │  95   │ Jan 15    │
│ Meta   ▶ │ Frontend Eng   │ ✓ → ○ → ○ → ○    │  88   │ Jan 18    │
│ Apple  ▼ │ iOS Developer  │ ✓ → ✓ → ✓ → ⏳   │  92   │ Jan 12    │
│          └─ [EXPANDED DETAIL BELOW] ─────────────────────────────  │
└────────────────────────────────────────────────────────────────────┘
```

**Progress Column Icons:**
- ✓ (green checkmark): Stage completed
- ⏳ (hourglass): Current stage (last completed + 1)
- ○ (empty circle): Not started
- Arrows show progression

#### Expanded View
```
┌─────────────────────────────────────────────────────────────────────┐
│ Apple  ▼ │ iOS Developer  │ ✓ → ✓ → ✓ → ⏳   │  92   │ Jan 12     │
├─────────────────────────────────────────────────────────────────────┤
│   Stage Progress                                                    │
│   ☑ Applied      Jan 12, 2024 10:00 AM                             │
│                  "Submitted through company careers page"           │
│                                                                     │
│   ☑ OA          Jan 17, 2024 2:30 PM                               │
│                  "Completed Codility assessment - 100% score"       │
│                                                                     │
│   ☑ Interview    Jan 25, 2024 11:00 AM                             │
│                  "Phone screen with hiring manager, went well"      │
│                                                                     │
│   ☐ Offer        [+ Add note when completed]                       │
│                                                                     │
│   Status: In Progress  [Mark as Rejected ▼]                        │
└─────────────────────────────────────────────────────────────────────┘
```

**Interaction:**
- Click row → toggle expand/collapse
- Click checkbox → auto-save to backend, show loading spinner briefly
- Click "Mark as Rejected" → show inline dropdown with rejection stage selector
- Notes field: auto-expand textarea, debounced save (500ms after typing stops)
- Polling: Don't collapse expanded rows on data refresh

#### Rejection UI
When user clicks "Mark as Rejected":
```
┌─────────────────────────────────────────────────────────────────┐
│   Status: In Progress  [Mark as Rejected ▼] ← CLICKED          │
│   ┌───────────────────────────────────────────────────────────┐ │
│   │ Rejected at stage:                                        │ │
│   │ ○ Applied  ○ OA  ● Interview  ○ Offer                     │ │
│   │                                                            │ │
│   │ Reason (optional):                                         │ │
│   │ ┌────────────────────────────────────────────────────────┐│ │
│   │ │ Failed technical round - struggled with system design ││ │
│   │ └────────────────────────────────────────────────────────┘│ │
│   │                                                            │ │
│   │ [Cancel]  [Mark as Rejected]                              │ │
│   └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Status Badge Updates

**New Badge Variants:**
- `suggested`: Purple "Suggested" badge
- `active`: Blue "In Progress" badge
- `rejected`: Red "Rejected (at OA)" badge - dynamically shows rejection stage
- `dismissed`: Gray "Dismissed" badge
- `failed`: Red "Failed" badge (system errors)

### Component Structure

**New Components:**
- `components/ui/job-stage-editor.tsx` - Expandable stage editor
- `components/ui/stage-progress.tsx` - Compact progress indicator (✓ → ⏳ → ○)
- `components/ui/rejection-form.tsx` - Inline rejection form

**Modified Components:**
- `app/dashboard/page.tsx` - Add expandable row logic
- `lib/api.ts` - Add `updateJobStages()` function

---

## Implementation Phases

### Phase 1: Database & Migrations
1. Create `JobStage` SQLModel class
2. Add rejection fields to `Job` model
3. Create Alembic migration with upgrade/downgrade logic
4. Test migration on fresh database
5. Test migration on database with existing jobs
6. Add schema version check to `db_sync.py`

### Phase 2: Backend API
1. Create `PUT /jobs/{id}/stages` endpoint
2. Modify `GET /jobs/{id}` to include stages (LEFT JOIN)
3. Modify `GET /jobs` to include stages
4. Modify `POST /apply` to create initial stage
5. Add Pydantic models for request/response
6. Write backend unit tests

### Phase 3: Frontend UI
1. Create `stage-progress.tsx` component (compact view)
2. Create `job-stage-editor.tsx` component (expanded view)
3. Create `rejection-form.tsx` component
4. Modify dashboard to support expandable rows
5. Add `updateJobStages()` API function
6. Implement auto-save with debouncing
7. Add loading states

### Phase 4: Testing & Verification
1. Test migration on hybrid database setup
2. Test stage updates (API → DB → UI refresh)
3. Test rejection workflow
4. Test polling doesn't collapse expanded rows
5. Test concurrent updates
6. Manual UI testing (mobile responsive, accessibility)

---

## Testing Strategy

### Database Layer Tests
- ✅ Fresh database: migration creates tables correctly
- ✅ Existing jobs: migration preserves data and maps statuses correctly
- ✅ Schema version check: detects mismatched Alembic versions
- ✅ Hybrid sync: disables sync when schemas differ
- ✅ Foreign key cascade: deleting job deletes stages

### API Layer Tests
- ✅ `PUT /jobs/{id}/stages`: Valid request updates database
- ✅ Invalid stage names return 400 error
- ✅ Completing stage sets `completed_at` timestamp
- ✅ Unchecking stage clears `completed_at`
- ✅ Rejection updates both `rejection_stage` and `rejection_reason`
- ✅ GET endpoints include stages in response

### Frontend Tests
- ✅ Expandable row toggles correctly
- ✅ Checkbox updates trigger API call
- ✅ Auto-save debounces note edits
- ✅ Rejection form submits and updates UI
- ✅ Polling refresh preserves expanded state
- ✅ Loading spinners show during API calls

### Integration Tests
- ✅ End-to-end: Apply job → check stages → mark rejected
- ✅ Hybrid mode: Update in SQLite → syncs to PostgreSQL
- ✅ Concurrent updates: Two users editing same job
- ✅ Migration rollback: Downgrade restores old schema

---

## Success Criteria

1. ✅ Users can track Applied/OA/Interview/Offer stages with timestamps
2. ✅ UI is clean and doesn't clutter the dashboard
3. ✅ No data loss during migration from old status model
4. ✅ Hybrid database mode continues to work
5. ✅ Stage updates persist across page refreshes
6. ✅ Rejection tracking works and displays correctly
7. ✅ All tests pass (database, API, frontend)

---

## Future Enhancements (Out of Scope)

- Statistics dashboard showing conversion funnel
- Multiple interview rounds (Interview 1, Interview 2, etc.)
- Email/calendar integration to auto-track stages
- Reminders/notifications for pending stages
- Export stage data to CSV for external analysis

---

## Open Questions

None - design approved and ready for implementation.
