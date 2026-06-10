"""Tests for the structured tailoring agent and the Part-B robustness fixes."""
from pathlib import Path
import asyncio
import sys
import unittest

import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool
from sqlalchemy.exc import IntegrityError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agents import ResumeTailorAgent
from core.llm_providers import StubProvider, _run_coro
from core.models import JobPosting
from core.resume_model import ResumeContent, Header, Role, ExperienceEntry, ProjectEntry
from database import Job


def _big_resume() -> ResumeContent:
    """A pool larger than the one-page budget, to test trimming."""
    return ResumeContent(
        header=Header(name="Alex Yuan", email="a@b.com", links=[]),
        experience=[
            ExperienceEntry(
                company=f"Co{i}",
                location="Remote",
                roles=[Role(title="Engineer", dates="2020 -- 2021")],
                bullets=[f"Bullet {j} for company {i}." for j in range(8)],
            )
            for i in range(8)
        ],
        projects=[
            ProjectEntry(name=f"Proj{i}", tech=["Python"], bullets=[f"Did {j}." for j in range(6)])
            for i in range(10)
        ],
    )


class TailorAgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = ResumeTailorAgent(client=StubProvider())
        self.job = JobPosting(
            company_name="Acme",
            job_title="Backend Engineer",
            summary="Build Python APIs",
            key_requirements=["Python", "FastAPI"],
        )

    def test_tailor_returns_resume_content(self):
        result = self.agent.tailor(_big_resume(), self.job)
        self.assertIsInstance(result, ResumeContent)

    def test_header_is_preserved_from_master(self):
        master = _big_resume()
        result = self.agent.tailor(master, self.job)
        self.assertEqual(result.header.name, master.header.name)

    def test_budget_is_enforced(self):
        master = _big_resume()
        trimmed = self.agent._enforce_budget(master.model_copy(deep=True), master)
        self.assertLessEqual(len(trimmed.experience), self.agent.MAX_EXPERIENCE)
        self.assertLessEqual(len(trimmed.projects), self.agent.MAX_PROJECTS)
        self.assertTrue(all(len(e.bullets) <= self.agent.MAX_BULLETS_PER_EXPERIENCE for e in trimmed.experience))
        self.assertTrue(all(len(p.bullets) <= self.agent.MAX_BULLETS_PER_PROJECT for p in trimmed.projects))

    def test_empty_selection_falls_back_to_master(self):
        master = _big_resume()
        empty = ResumeContent(header=master.header, experience=[], projects=[])
        restored = self.agent._enforce_budget(empty, master)
        self.assertTrue(restored.experience)
        self.assertTrue(restored.projects)


class RunCoroTimeoutTests(unittest.TestCase):
    def test_timeout_raises(self):
        async def slow():
            await asyncio.sleep(5)

        with self.assertRaises((TimeoutError, asyncio.TimeoutError)):
            _run_coro(slow(), timeout=0.05)

    def test_returns_value_without_timeout(self):
        async def quick():
            return 42

        self.assertEqual(_run_coro(quick(), timeout=5), 42)


class JobUrlUniquenessTests(unittest.TestCase):
    def test_duplicate_url_rejected(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            session.add(Job(url="http://dup.com", company="A", title="T1", status="suggested", retry_count=0))
            session.commit()
            session.add(Job(url="http://dup.com", company="B", title="T2", status="suggested", retry_count=0))
            with self.assertRaises(IntegrityError):
                session.commit()


if __name__ == "__main__":
    unittest.main()
