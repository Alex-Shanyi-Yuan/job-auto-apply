from datetime import datetime
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlmodel import Session, select

from core import db_sync
from database import Job, JobSource, Settings, create_db_and_tables_for_engine, create_engine_for_url


class DatabaseSyncTests(unittest.TestCase):
    def _sqlite_url(self, directory: str, filename: str) -> str:
        return f"sqlite:///{Path(directory) / filename}"

    def _seed_store(self, engine, *, suffix: str) -> None:
        create_db_and_tables_for_engine(engine)
        with Session(engine) as session:
            session.add(Settings(key="global_filter", value=f"filter-{suffix}", updated_at=datetime(2020, 1, 1)))
            session.add(
                JobSource(
                    url=f"https://example.com/{suffix}",
                    name=f"source-{suffix}",
                    filter_prompt="",
                    created_at=datetime(2020, 1, 2),
                    updated_at=datetime(2020, 1, 3),
                )
            )
            session.add(
                Job(
                    url=f"https://example.com/job/{suffix}",
                    company="Example Co",
                    title=f"Engineer {suffix}",
                    status="suggested",
                    created_at=datetime(2020, 1, 4),
                    updated_at=datetime(2020, 1, 5),
                )
            )
            session.commit()

    def test_create_engine_for_url_creates_sqlite_parent_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "nested" / "autocareer.db"
            url = f"sqlite:///{nested_path}"

            create_engine_for_url(url)

            self.assertTrue(nested_path.parent.exists())

    def test_copy_store_preserves_updated_at_and_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_url = self._sqlite_url(temp_dir, "source.db")
            target_url = self._sqlite_url(temp_dir, "target.db")
            source_engine = create_engine_for_url(source_url)
            target_engine = create_engine_for_url(target_url)
            self.addCleanup(source_engine.dispose)
            self.addCleanup(target_engine.dispose)

            self._seed_store(source_engine, suffix="a")

            db_sync.copy_store(source_engine, target_engine)

            with Session(target_engine) as session:
                self.assertEqual(len(session.exec(select(Settings)).all()), 1)
                self.assertEqual(len(session.exec(select(JobSource)).all()), 1)
                self.assertEqual(len(session.exec(select(Job)).all()), 1)

                copied_source = session.exec(select(JobSource)).one()
                copied_job = session.exec(select(Job)).one()
                self.assertEqual(copied_source.updated_at, datetime(2020, 1, 3))
                self.assertEqual(copied_job.updated_at, datetime(2020, 1, 5))

    def test_updated_at_changes_on_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = create_engine_for_url(self._sqlite_url(temp_dir, "update.db"))
            self.addCleanup(engine.dispose)
            create_db_and_tables_for_engine(engine)

            with Session(engine) as session:
                source = JobSource(
                    url="https://example.com/source",
                    name="initial",
                    filter_prompt="",
                    created_at=datetime(2020, 1, 2),
                    updated_at=datetime(2000, 1, 1),
                )
                job = Job(
                    url="https://example.com/job",
                    company="Example Co",
                    title="Initial",
                    status="suggested",
                    created_at=datetime(2020, 1, 4),
                    updated_at=datetime(2000, 1, 1),
                )
                session.add(source)
                session.add(job)
                session.commit()

                source.name = "updated"
                job.title = "Updated"
                session.add(source)
                session.add(job)
                session.commit()

                refreshed_source = session.exec(select(JobSource)).one()
                refreshed_job = session.exec(select(Job)).one()

                self.assertGreater(refreshed_source.updated_at, datetime(2000, 1, 1))
                self.assertGreater(refreshed_job.updated_at, datetime(2000, 1, 1))

    def test_migrate_postgres_to_sqlite_with_sqlite_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_url = self._sqlite_url(temp_dir, "postgres_like.db")
            target_url = self._sqlite_url(temp_dir, "sqlite_like.db")
            source_engine = create_engine_for_url(source_url)
            target_engine = create_engine_for_url(target_url)
            self.addCleanup(source_engine.dispose)
            self.addCleanup(target_engine.dispose)
            self._seed_store(source_engine, suffix="m")

            with patch.object(db_sync, "is_postgres_reachable", return_value=True):
                result = db_sync.migrate_postgres_to_sqlite(source_url, target_url)

            self.assertTrue(result["row_counts_match"])

            with Session(target_engine) as session:
                self.assertEqual(len(session.exec(select(Settings)).all()), 1)
                self.assertEqual(len(session.exec(select(JobSource)).all()), 1)
                self.assertEqual(len(session.exec(select(Job)).all()), 1)


if __name__ == "__main__":
    unittest.main()