from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, text  # type: ignore[import-not-found]
from sqlmodel import Session, delete, select  # type: ignore[import-not-found]

from database import (
    Job,
    JobSource,
    Settings,
    create_db_and_tables_for_engine,
    create_engine_for_url,
    get_postgres_engine,
    get_sqlite_engine,
    DATABASE_BACKEND,
    SQLITE_DATABASE_URL,
    POSTGRES_DATABASE_URL,
)

# Alembic imports for schema version checking
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

import logging
logger = logging.getLogger(__name__)


def get_alembic_version(engine):
    """Get current Alembic migration version from database."""
    try:
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    except Exception as e:
        logger.error(f"Failed to get Alembic version: {e}")
        return None


def check_schema_parity():
    """Check if SQLite and PostgreSQL have the same schema version."""
    if DATABASE_BACKEND != "hybrid":
        return True
    
    try:
        sqlite_engine = create_engine_for_url(SQLITE_DATABASE_URL)
        postgres_engine = create_engine_for_url(POSTGRES_DATABASE_URL)
        
        sqlite_version = get_alembic_version(sqlite_engine)
        postgres_version = get_alembic_version(postgres_engine)
        
        if sqlite_version != postgres_version:
            logger.warning(
                f"Schema version mismatch: SQLite={sqlite_version}, PostgreSQL={postgres_version}. "
                "Sync disabled until schemas match. Run 'alembic upgrade head' in both environments."
            )
            return False
        
        logger.info(f"Schema parity confirmed: both databases at version {sqlite_version}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to check schema parity: {e}")
        return False

@dataclass
class StoreStats:
    name: str
    settings_count: int
    jobsource_count: int
    job_count: int
    latest_timestamp: Optional[datetime]
    max_jobsource_id: int
    max_job_id: int

    @property
    def total_rows(self) -> int:
        return self.settings_count + self.jobsource_count + self.job_count

    @property
    def rank_tuple(self):
        latest = self.latest_timestamp or datetime.min
        tertiary = self.max_jobsource_id + self.max_job_id
        return (self.total_rows, latest, tertiary)


def is_postgres_reachable(postgres_engine) -> bool:
    try:
        with postgres_engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


def _scalar_int(session: Session, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


def _get_store_stats(name: str, engine_obj) -> StoreStats:
    with Session(engine_obj) as session:
        settings_count = _scalar_int(session, select(func.count()).select_from(Settings))
        jobsource_count = _scalar_int(session, select(func.count()).select_from(JobSource))
        job_count = _scalar_int(session, select(func.count()).select_from(Job))

        settings_latest = session.exec(select(func.max(Settings.updated_at))).one()
        source_latest = session.exec(
            select(func.max(func.coalesce(JobSource.updated_at, JobSource.last_scraped_at, JobSource.created_at)))
        ).one()
        job_latest = session.exec(select(func.max(func.coalesce(Job.updated_at, Job.created_at)))).one()

        latest_candidates = [t for t in [settings_latest, source_latest, job_latest] if t is not None]
        latest_timestamp = max(latest_candidates) if latest_candidates else None

        max_jobsource_id = _scalar_int(session, select(func.max(JobSource.id)))
        max_job_id = _scalar_int(session, select(func.max(Job.id)))

    return StoreStats(
        name=name,
        settings_count=settings_count,
        jobsource_count=jobsource_count,
        job_count=job_count,
        latest_timestamp=latest_timestamp,
        max_jobsource_id=max_jobsource_id,
        max_job_id=max_job_id,
    )


def _dump_store(engine_obj) -> Dict[str, List[Dict[str, Any]]]:
    with Session(engine_obj) as session:
        settings = session.exec(select(Settings)).all()
        sources = session.exec(select(JobSource)).all()
        jobs = session.exec(select(Job)).all()

        return {
            "settings": [
                {
                    "key": row.key,
                    "value": row.value,
                    "updated_at": row.updated_at,
                }
                for row in settings
            ],
            "jobsource": [
                {
                    "id": row.id,
                    "url": row.url,
                    "name": row.name,
                    "filter_prompt": row.filter_prompt,
                    "last_scraped_at": row.last_scraped_at,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in sources
            ],
            "job": [
                {
                    "id": row.id,
                    "url": row.url,
                    "company": row.company,
                    "title": row.title,
                    "status": row.status,
                    "requirements": row.requirements,
                    "pdf_path": row.pdf_path,
                    "score": row.score,
                    "source_id": row.source_id,
                    "error_message": row.error_message,
                    "created_at": row.created_at,
                    "updated_at": row.updated_at,
                }
                for row in jobs
            ],
        }


def _load_store(engine_obj, payload: Dict[str, List[Dict[str, Any]]]) -> None:
    with Session(engine_obj) as session:
        session.exec(delete(Job))
        session.exec(delete(JobSource))
        session.exec(delete(Settings))

        for row in payload["settings"]:
            session.add(Settings(**row))

        valid_source_ids = set()

        for row in payload["jobsource"]:
            session.add(JobSource(**row))
            if row.get("id") is not None:
                valid_source_ids.add(row["id"])

        # Persist source rows first so SQLite FK checks pass when inserting jobs.
        session.commit()

        for row in payload["job"]:
            # Older Postgres datasets may contain orphaned source_id values.
            # SQLite enforces FK constraints, so normalize invalid references.
            source_id = row.get("source_id")
            if source_id is not None and source_id not in valid_source_ids:
                row = {**row, "source_id": None}
            session.add(Job(**row))

        session.commit()


def copy_store(source_engine, target_engine) -> None:
    create_db_and_tables_for_engine(source_engine)
    create_db_and_tables_for_engine(target_engine)
    payload = _dump_store(source_engine)
    _load_store(target_engine, payload)


def sync_databases():
    """Sync data between SQLite and PostgreSQL in hybrid mode."""
    if DATABASE_BACKEND != "hybrid":
        return {"status": "skipped", "reason": "not in hybrid mode"}
    
    # Check schema parity first
    if not check_schema_parity():
        return {"status": "disabled", "reason": "schema version mismatch"}
    
    # ... rest of existing sync logic
    sqlite_engine = get_sqlite_engine()
    postgres_engine = get_postgres_engine()

    create_db_and_tables_for_engine(sqlite_engine)

    if not is_postgres_reachable(postgres_engine):
        return {
            "status": "skipped",
            "reason": "postgres_unreachable",
        }

    create_db_and_tables_for_engine(postgres_engine)

    sqlite_stats = _get_store_stats("sqlite", sqlite_engine)
    postgres_stats = _get_store_stats("postgres", postgres_engine)

    if postgres_stats.rank_tuple >= sqlite_stats.rank_tuple:
        winner = "postgres"
        copy_store(postgres_engine, sqlite_engine)
    else:
        winner = "sqlite"
        copy_store(sqlite_engine, postgres_engine)

    final_sqlite_stats = _get_store_stats("sqlite", sqlite_engine)
    final_postgres_stats = _get_store_stats("postgres", postgres_engine)

    return {
        "status": "synced",
        "winner": winner,
        "before": {
            "sqlite": sqlite_stats.__dict__,
            "postgres": postgres_stats.__dict__,
        },
        "after": {
            "sqlite": final_sqlite_stats.__dict__,
            "postgres": final_postgres_stats.__dict__,
        },
    }

# For backward compatibility, keep the old function name
reconcile_postgres_and_sqlite = sync_databases


def migrate_postgres_to_sqlite(postgres_url: str, sqlite_url: str) -> Dict[str, Any]:
    postgres_engine = create_engine_for_url(postgres_url)
    sqlite_engine = create_engine_for_url(sqlite_url)

    if not is_postgres_reachable(postgres_engine):
        raise RuntimeError("PostgreSQL is not reachable with the provided URL")

    copy_store(postgres_engine, sqlite_engine)

    postgres_stats = _get_store_stats("postgres", postgres_engine)
    sqlite_stats = _get_store_stats("sqlite", sqlite_engine)

    return {
        "status": "migrated",
        "postgres": postgres_stats.__dict__,
        "sqlite": sqlite_stats.__dict__,
        "row_counts_match": (
            postgres_stats.settings_count == sqlite_stats.settings_count
            and postgres_stats.jobsource_count == sqlite_stats.jobsource_count
            and postgres_stats.job_count == sqlite_stats.job_count
        ),
    }
