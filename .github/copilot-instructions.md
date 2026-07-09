# AutoCareer — Copilot Instructions

AutoCareer is a self-hosted job automation platform (Next.js frontend, FastAPI backend,
Playwright scraper, PostgreSQL/SQLite) that discovers, scores, and applies to jobs with
AI-tailored resumes.

**The canonical AI-assistant instructions live in [`CLAUDE.md`](../CLAUDE.md) at the repo
root — read that file first.** It contains the architecture, key source files, development
commands, environment variables, code patterns, and the documentation-update policy
(Knowledge Retention Policy + Documentation Map). Do not add project knowledge to this
file; it exists only so GitHub Copilot has a pointer.

Essentials:

- Services run via `docker-compose up --build` — frontend :3000, tailor API :8000, scraper :8001, postgres :5432.
- Backend tests: `cd backend/services/resume-tailor && TESTING=true <repo-root>/.venv/bin/python -m pytest tests/ -q` (deps live in the repo-root `.venv`).
- All frontend API calls go through `frontend/lib/api.ts` — add new endpoints there.
- When you change code, update the docs listed in CLAUDE.md's Documentation Map in the same commit.
