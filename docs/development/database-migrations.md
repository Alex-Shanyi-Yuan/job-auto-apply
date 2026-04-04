# Database Migrations

This guide covers database schema management using Alembic, including migration workflows, hybrid mode synchronization, and troubleshooting.

## Overview

AutoCareer uses **Alembic** for database migrations and **SQLModel** for ORM models. The system supports three database backends:

- **SQLite** — File-based, best for local development
- **PostgreSQL** — Production-ready, supports concurrent access
- **Hybrid** — Bidirectional sync between PostgreSQL and SQLite

## Quick Reference

```bash
# Apply migrations (Docker)
docker-compose exec tailor alembic upgrade head

# Apply migrations (local)
cd backend/services/resume-tailor
alembic upgrade head

# Create new migration (auto-detect changes)
docker-compose exec tailor alembic revision --autogenerate -m "add column to job table"

# View migration history
docker-compose exec tailor alembic history

# Rollback one migration
docker-compose exec tailor alembic downgrade -1

# Check current version
docker-compose exec tailor alembic current
```

## Database Backend Configuration

Set in `.env` or `backend/services/resume-tailor/.env`:

```bash
# Choose backend: sqlite | postgres | hybrid
DATABASE_BACKEND=sqlite

# SQLite configuration
SQLITE_DATABASE_URL=sqlite:///./data/autocareer.db

# PostgreSQL configuration
POSTGRES_DATABASE_URL=postgresql://user:password@postgres:5432/autocareer

# Hybrid mode settings
DB_SYNC_ENABLED=true          # Enable bidirectional sync
SYNC_ON_BOOT=true             # Sync PostgreSQL → SQLite on startup
SYNC_ON_SHUTDOWN=true         # Sync SQLite → PostgreSQL on shutdown
```

### Backend Behavior

| Backend | Runtime Database | Persistence | Use Case |
|---------|-----------------|-------------|----------|
| `sqlite` | SQLite only | File-based | Local development, testing |
| `postgres` | PostgreSQL only | Server-based | Production, shared environments |
| `hybrid` | Both (synced) | Both | Development portability, migration |

## Alembic Workflow

### 1. Creating Migrations

Migrations are auto-generated from SQLModel schema changes.

**Step 1: Modify the model**

Edit `backend/services/resume-tailor/database.py`:

```python
class Job(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str = Field(unique=True, index=True)
    company: str
    title: str
    status: str
    score: Optional[int] = None
    
    # New field
    priority: Optional[str] = Field(default="normal")  # Add this
```

**Step 2: Generate migration**

```bash
docker-compose exec tailor alembic revision --autogenerate -m "add priority to job"
```

This creates a file like `migrations/versions/abc123_add_priority_to_job.py`.

**Step 3: Review the migration**

**⚠️ Always review auto-generated migrations** before applying. Alembic may not detect:
- Complex index changes
- Enum type modifications
- Data migrations

Open the generated file:

```bash
code backend/services/resume-tailor/migrations/versions/abc123_add_priority_to_job.py
```

Verify:
- [ ] Column additions are correct
- [ ] Default values are appropriate
- [ ] No unintended drops or renames

**Step 4: Apply migration**

```bash
docker-compose exec tailor alembic upgrade head
```

Or if running locally:
```bash
cd backend/services/resume-tailor
alembic upgrade head
```

### 2. Manual Migrations

For complex changes (data migrations, custom logic), create a blank migration:

```bash
docker-compose exec tailor alembic revision -m "migrate old status values"
```

Edit the generated file:

```python
from alembic import op
import sqlalchemy as sa

def upgrade():
    # Custom SQL or Python logic
    op.execute("""
        UPDATE job 
        SET status = 'applied' 
        WHERE status = 'pending'
    """)

def downgrade():
    op.execute("""
        UPDATE job 
        SET status = 'pending' 
        WHERE status = 'applied'
    """)
```

### 3. Running Migrations

**On container startup:**
Migrations run automatically via `entrypoint.sh` when the `tailor` service starts:

```bash
docker-compose up tailor
# Migrations applied before server starts
```

**Manually:**
```bash
# Upgrade to latest
docker-compose exec tailor alembic upgrade head

# Upgrade by specific number of revisions
docker-compose exec tailor alembic upgrade +2

# Downgrade by one
docker-compose exec tailor alembic downgrade -1

# Downgrade to specific revision
docker-compose exec tailor alembic downgrade abc123
```

### 4. Viewing Migration Status

```bash
# Current database version
docker-compose exec tailor alembic current

# Migration history
docker-compose exec tailor alembic history

# Show detailed info
docker-compose exec tailor alembic history --verbose
```

## Hybrid Mode Explained

Hybrid mode allows **bidirectional synchronization** between PostgreSQL and SQLite. This is useful for:

- **Development portability:** Work offline with SQLite, sync to PostgreSQL when online
- **Data migration:** Move data from PostgreSQL to SQLite or vice versa
- **Testing:** Use SQLite for fast tests, PostgreSQL for integration tests

### How Hybrid Sync Works

**On Application Startup (SYNC_ON_BOOT=true):**
1. Connect to PostgreSQL
2. Read all data from PostgreSQL tables
3. Write data to SQLite (merging by primary key)
4. Application uses **SQLite** for all runtime queries

**On Application Shutdown (SYNC_ON_SHUTDOWN=true):**
1. Read all data from SQLite tables
2. Write data back to PostgreSQL (merging by primary key)
3. PostgreSQL now has latest changes

**Merge Strategy:**
- Primary keys match → Update existing row
- Primary key not found → Insert new row
- No automatic deletion (prevents accidental data loss)

### Enabling Hybrid Mode

```bash
# In .env
DATABASE_BACKEND=hybrid
DB_SYNC_ENABLED=true
SYNC_ON_BOOT=true
SYNC_ON_SHUTDOWN=true
```

**Both connection strings required:**
```bash
SQLITE_DATABASE_URL=sqlite:///./data/autocareer.db
POSTGRES_DATABASE_URL=postgresql://user:password@postgres:5432/autocareer
```

### Manual Sync Commands

Run sync manually using `core/db_sync.py`:

```bash
# Sync PostgreSQL → SQLite
docker-compose exec tailor python -c "
from core.db_sync import sync_postgres_to_sqlite
sync_postgres_to_sqlite()
print('Synced PostgreSQL → SQLite')
"

# Sync SQLite → PostgreSQL
docker-compose exec tailor python -c "
from core.db_sync import sync_sqlite_to_postgres
sync_sqlite_to_postgres()
print('Synced SQLite → PostgreSQL')
"
```

### One-Time Migration Script

For a complete PostgreSQL → SQLite export:

```bash
docker-compose exec tailor python scripts/migrate_postgres_to_sqlite.py
```

This script:
1. Dumps all PostgreSQL data to SQLite
2. Preserves primary keys and timestamps
3. Logs skipped rows (e.g., constraint violations)
4. Useful when switching from `postgres` → `sqlite` backend

## Migration Best Practices

### 1. Always Review Auto-Generated Migrations

Alembic's `--autogenerate` is helpful but not perfect:

**It detects:**
- ✅ New columns
- ✅ Removed columns
- ✅ Changed column types
- ✅ New tables

**It may miss:**
- ❌ Renamed columns (appears as drop + add)
- ❌ Changed indexes
- ❌ Custom constraints
- ❌ Enum changes (SQLite doesn't enforce enums)

**Solution:** Always inspect generated migrations and edit as needed.

### 2. Test Migrations Locally First

```bash
# Create test database
cp data/autocareer.db data/autocareer.db.backup

# Run migration
alembic upgrade head

# Verify schema
sqlite3 data/autocareer.db ".schema job"

# Rollback if needed
alembic downgrade -1
```

### 3. Use Descriptive Migration Messages

**❌ Bad:**
```bash
alembic revision --autogenerate -m "changes"
```

**✅ Good:**
```bash
alembic revision --autogenerate -m "add priority and deadline columns to job table"
```

### 4. Handle Data Migrations Carefully

When changing data types or adding constraints:

```python
def upgrade():
    # Step 1: Add new column with nullable=True
    op.add_column('job', sa.Column('score_new', sa.Integer(), nullable=True))
    
    # Step 2: Migrate data
    op.execute("UPDATE job SET score_new = CAST(score AS INTEGER)")
    
    # Step 3: Drop old column
    op.drop_column('job', 'score')
    
    # Step 4: Rename new column
    op.alter_column('job', 'score_new', new_column_name='score', nullable=False)
```

### 5. Keep Migrations Small and Focused

**❌ One migration with multiple unrelated changes:**
```bash
alembic revision --autogenerate -m "add priority, fix status enum, add deadline"
```

**✅ Separate migrations:**
```bash
alembic revision --autogenerate -m "add priority column to job"
alembic revision --autogenerate -m "migrate status enum values"
alembic revision --autogenerate -m "add deadline column to job"
```

### 6. Never Edit Applied Migrations

Once a migration is applied to a shared database:
- ❌ Don't edit the migration file
- ❌ Don't delete the migration file
- ✅ Create a new migration to fix issues

**Exception:** Local development with no shared database.

## Schema Inspection

### SQLite

```bash
# Open SQLite shell
docker-compose exec tailor sqlite3 data/autocareer.db

# View schema
.schema job

# View all tables
.tables

# Query data
SELECT * FROM job LIMIT 5;

# Exit
.quit
```

### PostgreSQL

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U postgres -d autocareer

# View schema
\d job

# View all tables
\dt

# Query data
SELECT * FROM job LIMIT 5;

# Exit
\q
```

## Troubleshooting

### Migration Fails: "Target database is not up to date"

**Cause:** Database is ahead of migration files (e.g., pulled old code)

**Fix:**
```bash
# Check current version
docker-compose exec tailor alembic current

# Downgrade to a known good version
docker-compose exec tailor alembic downgrade <revision>

# Or reset database (⚠️ deletes all data)
docker-compose down -v
docker-compose up --build
```

### Migration Fails: "Column already exists"

**Cause:** Database schema out of sync with migrations

**Fix 1: Stamp the database**
```bash
# Mark current schema as a specific revision (no changes applied)
docker-compose exec tailor alembic stamp head
```

**Fix 2: Reset database**
```bash
# ⚠️ Deletes all data
rm backend/services/resume-tailor/data/autocareer.db
alembic upgrade head
```

### Auto-Generate Detects No Changes

**Cause 1:** Models not imported in `database.py`  
**Fix:** Ensure all SQLModel classes are in `database.py`

**Cause 2:** Database already matches models  
**Fix:** Check `alembic current` to verify version

### Hybrid Sync Fails: "Foreign key constraint violation"

**Cause:** Sync order doesn't respect foreign keys

**Fix:** Edit `core/db_sync.py` to sync tables in dependency order:
```python
# Sync in order: Settings → JobSource → Job
sync_table(Settings, src_session, dst_session)
sync_table(JobSource, src_session, dst_session)
sync_table(Job, src_session, dst_session)
```

### Migration Slow on Large Database

**Cause:** Adding indexes or constraints on large tables

**Fix:** Run migration during low-traffic period or:
```python
# Use concurrent index creation (PostgreSQL)
op.create_index('ix_job_score', 'job', ['score'], postgresql_concurrently=True)
```

## Migration Checklist

Before applying migrations to production:

- [ ] Migration reviewed and tested locally
- [ ] Backup database (PostgreSQL) or copy file (SQLite)
- [ ] Migration is reversible (downgrade works)
- [ ] No destructive changes without data migration
- [ ] Application can handle both old and new schema during deployment
- [ ] Environment variables updated if needed
- [ ] Team notified of schema changes

## Advanced: Branching Migrations

When multiple developers create migrations concurrently:

```bash
# Merge multiple heads
docker-compose exec tailor alembic merge <rev1> <rev2> -m "merge migrations"

# Apply merge
docker-compose exec tailor alembic upgrade head
```

## Additional Resources

- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [SQLModel Documentation](https://sqlmodel.tiangolo.com/)
- [Development Guide](./README.md) — Local setup
- [Testing Strategies](./testing.md) — Testing with different backends
