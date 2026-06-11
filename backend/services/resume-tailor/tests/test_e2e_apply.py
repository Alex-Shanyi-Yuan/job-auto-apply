"""True end-to-end test of the apply pipeline against a running stack.

Unlike the rest of the suite (which stubs the LLM), this test drives the REAL
deployed services over HTTP: scraper fetch -> Claude parse -> Claude tailor ->
LaTeX render -> pdflatex. It is therefore skipped by default and only runs
when explicitly requested:

    # 1. Start the stack (CLAUDE_CODE_OAUTH_TOKEN must be set for the tailor)
    docker compose --profile postgres up -d --build

    # 2. Run just this test from the repo-root venv
    cd backend/services/resume-tailor
    RUN_E2E=true TESTING=true ../../../.venv/bin/python -m pytest tests/test_e2e_apply.py -q

Notes:
- The job URL is intentionally hardcoded; POST /apply reuses the existing job
  row for a known URL (no unique-index conflict), so the test is rerunnable.
- "active" is the pipeline's success terminal status (set together with
  pdf_path in process_application); "failed" is the error terminal status.
- A full run takes minutes: each Claude call shells out to the `claude` CLI
  and the tailoring prompt carries the entire master content pool. Budget is
  controlled by E2E_TIMEOUT_SECONDS (default 30 min).
"""
from __future__ import annotations

import os
import time
import unittest

import requests

E2E_ENABLED = os.getenv("RUN_E2E", "").strip().lower() in {"1", "true", "yes"}
BASE_URL = os.getenv("E2E_BASE_URL", "http://localhost:8000").rstrip("/")
JOB_URL = "https://openai.com/careers/backend-software-engineer-api-multicloud-san-francisco/"
TIMEOUT_SECONDS = int(os.getenv("E2E_TIMEOUT_SECONDS", "1800"))
POLL_INTERVAL_SECONDS = 10

TERMINAL_STATUSES = {"active", "failed"}


@unittest.skipUnless(
    E2E_ENABLED,
    "End-to-end test: requires the Docker stack and a Claude token; run with RUN_E2E=true",
)
class ApplyEndToEndTests(unittest.TestCase):
    """POST /apply with a real job URL and assert a tailored PDF comes out."""

    def test_apply_generates_tailored_resume_pdf(self):
        # The stack must be healthy and not blocking /apply before we start.
        health = requests.get(f"{BASE_URL}/health", timeout=15).json()
        self.assertFalse(
            health.get("apply_blocked"),
            f"/apply is blocked by startup checks: {health.get('apply_block_reason')}",
        )

        response = requests.post(f"{BASE_URL}/apply", json={"url": JOB_URL}, timeout=30)
        self.assertEqual(response.status_code, 200, response.text)
        job = response.json()
        job_id = job["id"]
        self.assertEqual(job["status"], "processing")

        job = self._poll_until_terminal(job_id)

        self.assertNotEqual(
            job["status"], "failed",
            f"Pipeline failed for job {job_id}: {job.get('error_message')}",
        )
        self.assertEqual(job["status"], "active")
        self.assertEqual(job["company"], "OpenAI")
        self.assertIn("Backend Software Engineer", job["title"])
        self.assertTrue(job["requirements"], "JobParsingAgent extracted no requirements")
        self.assertTrue(job["pdf_path"], "No pdf_path recorded on the job")

        pdf = requests.get(f"{BASE_URL}/jobs/{job_id}/pdf", timeout=30)
        self.assertEqual(pdf.status_code, 200, "PDF download failed")
        self.assertTrue(pdf.content.startswith(b"%PDF"), "Downloaded file is not a PDF")
        self.assertGreater(len(pdf.content), 10_000, "PDF suspiciously small")

    def _poll_until_terminal(self, job_id: int) -> dict:
        deadline = time.monotonic() + TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            job = requests.get(f"{BASE_URL}/jobs/{job_id}", timeout=15).json()
            if job["status"] in TERMINAL_STATUSES:
                return job
            time.sleep(POLL_INTERVAL_SECONDS)
        self.fail(
            f"Job {job_id} did not reach a terminal status within {TIMEOUT_SECONDS}s "
            f"(last status: {job['status']})"
        )


if __name__ == "__main__":
    unittest.main()
