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
)


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

        for row in payload["jobsource"]:
            session.add(JobSource(**row))

        for row in payload["job"]:
            session.add(Job(**row))

        session.commit()


def copy_store(source_engine, target_engine) -> None:
    create_db_and_tables_for_engine(source_engine)
    create_db_and_tables_for_engine(target_engine)
    payload = _dump_store(source_engine)
    _load_store(target_engine, payload)


def reconcile_postgres_and_sqlite() -> Dict[str, Any]:
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
