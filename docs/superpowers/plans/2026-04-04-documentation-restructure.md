# Documentation Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize AutoCareer documentation from 7 scattered root-level files into a clear `docs/` directory structure with feature prioritization.

**Architecture:** Five-phase approach following the approved design spec. Phase 1 creates directory structure, Phase 2 writes new content, Phase 3 migrates existing content, Phase 4 simplifies root/service READMEs, Phase 5 documents AI setup. All changes are documentation-only—no code modifications.

**Tech Stack:** Markdown, Git

---

## Spec Reference

This plan implements: `docs/superpowers/specs/2026-04-04-documentation-restructure-design.md`

**Key requirements:**
- Create `docs/` with 6 subdirectories (getting-started, architecture, features, development, enhancements, api)
- Maintain CLAUDE.md and TODO.todo untouched in root
- Simplify backend/frontend READMEs to pointers
- Extract Essential + Very Useful features from HARNESS_ENHANCEMENTS.md to roadmap
- Delete 5 root-level files after migration: PROJECT_README.md, FolderStruct.md, HARNESS_ENHANCEMENTS.md, IMPLEMENTATION_VERIFICATION_REPORT.md, SCRAPER_PLUGIN_DESIGN_DOC.md

---

## PHASE 1: Create Documentation Structure

### Task 1: Create Directory Structure

**Files:**
- Create: `docs/` (with subdirectories)

- [ ] **Create all documentation directories**

```bash
cd /Users/alexyuan/Documents/job-auto-apply
mkdir -p docs/getting-started
mkdir -p docs/architecture
mkdir -p docs/features
mkdir -p docs/development
mkdir -p docs/enhancements/archive
mkdir -p docs/api
mkdir -p docs/superpowers/specs
mkdir -p docs/superpowers/plans
```

- [ ] **Verify directory structure**

```bash
tree docs -L 2
```

Expected: 8 directories (getting-started, architecture, features, development, enhancements with archive/, api, superpowers with specs/ and plans/)

- [ ] **Commit structure**

```bash
git add docs/
git commit -m "docs: create documentation directory structure

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Create Navigation Hub

**Files:**
- Create: `docs/README.md`

- [ ] **Create docs/README.md**

Full navigation hub with:
- "New Here? Start Here!" section linking to quickstart, architecture, roadmap
- Organized sections: Getting Started, Architecture, Features, Development, Enhancements, API
- Quick links for troubleshooting, API keys, contributing
- Each section lists all documents with brief descriptions

- [ ] **Commit navigation hub**

```bash
git add docs/README.md
git commit -m "docs: add navigation hub

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## PHASE 2: Write New Documentation Content

### Task 3: Quickstart Guide

**Files:**
- Create: `docs/getting-started/quickstart.md`

- [ ] **Create quickstart.md**

Content:
- Prerequisites (Docker, Gemini API key, Git)
- 5-step installation (clone, configure .env, add resume, start services, open UI)
- First run checklist (add source, run scan, verify jobs)
- Stopping services
- Development mode instructions

- [ ] **Commit quickstart**

```bash
git add docs/getting-started/quickstart.md
git commit -m "docs: add quickstart guide

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: Environment Setup Guide

**Files:**
- Create: `docs/getting-started/environment-setup.md`

- [ ] **Create environment-setup.md**

Content:
- Configuration file location
- Required variables (GOOGLE_API_KEY with link)
- Database configuration (hybrid/postgres/sqlite modes explained)
- Service URLs
- Master resume path
- Performance tuning (RATE_LIMIT_DELAY, MAX_CONCURRENT_*)
- LLM configuration (RESUME_TAILOR_LLM_MODE)
- Frontend configuration (NEXT_PUBLIC_API_URL)
- Complete example .env file
- Troubleshooting section

- [ ] **Commit environment setup**

```bash
git add docs/getting-started/environment-setup.md
git commit -m "docs: add environment setup guide

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 5: Deployment Guide

**Files:**
- Create: `docs/getting-started/deployment.md`

- [ ] **Create deployment.md**

Content:
- Docker architecture table (4 services)
- Starting/stopping services
- Health checks (docker-compose ps, curl endpoints)
- Database management (migrations, psql access, backup)
- Troubleshooting (port conflicts, missing env vars, DB connection, build failures, frontend issues, PDF generation, memory, scraper blocking)
- Performance tips
- Rebuilding after changes

- [ ] **Commit deployment guide**

```bash
git add docs/getting-started/deployment.md
git commit -m "docs: add deployment guide

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 6: Architecture Overview

**Files:**
- Create: `docs/architecture/overview.md`
- Read: `PROJECT_README.md`
- Read: `FolderStruct.md`

- [ ] **Merge PROJECT_README + FolderStruct into overview.md**

Content to extract:
- System architecture (4 microservices)
- Service responsibilities (from PROJECT_README §2)
- Technology stack per service
- Database schema (Settings, JobSource, Job tables)
- Directory structure with explanations (from FolderStruct)
- Inter-service communication (Frontend → Tailor → Scraper)

- [ ] **Commit architecture overview**

```bash
git add docs/architecture/overview.md
git commit -m "docs: add architecture overview

Merge content from PROJECT_README and FolderStruct

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 7: Data Flow Documentation

**Files:**
- Create: `docs/architecture/data-flow.md`

- [ ] **Create data-flow.md**

Content:
- Job discovery workflow (source config → scan → discovery agent → scoring → suggestions)
- Resume tailoring workflow (apply → scrape → parse → tailor → compile → PDF)
- Application tracking workflow (status transitions)
- Text-based sequence diagrams for each flow

- [ ] **Commit data flow**

```bash
git add docs/architecture/data-flow.md
git commit -m "docs: add data flow documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 8: Technology Stack Documentation

**Files:**
- Create: `docs/architecture/technology-stack.md`

- [ ] **Create technology-stack.md**

Content:
- Frontend stack (Next.js 14 App Router, TypeScript, shadcn/ui, Tailwind)
- Backend stack (Python 3.11, FastAPI, SQLModel, Alembic)
- AI stack (Google Gemini Pro, structured output via Pydantic)
- Scraping stack (Playwright, BeautifulSoup)
- Database stack (PostgreSQL, SQLite, hybrid mode)
- PDF stack (TeX Live, pdflatex)
- Rationale for each choice

- [ ] **Commit technology stack**

```bash
git add docs/architecture/technology-stack.md
git commit -m "docs: add technology stack documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 9: Job Discovery Feature Documentation

**Files:**
- Create: `docs/features/job-discovery.md`
- Read: `SCRAPER_PLUGIN_DESIGN_DOC.md`

- [ ] **Integrate SCRAPER_PLUGIN_DESIGN_DOC into job-discovery.md**

Content:
- How AI discovery works (JobDiscoveryAgent)
- Source configuration (URL, filter, last_scraped_at)
- Global filter vs source-specific filter
- Scraper plugin architecture (domain manifests, registry routing)
- Supported job sites (Google, LinkedIn, Netflix, Jane Street, OpenAI, Anthropic)
- Parallel processing (MAX_CONCURRENT_SOURCES, MAX_CONCURRENT_JOBS)
- URL resolution (relative → absolute)
- Scan reports (added vs skipped jobs, skip reasons)

- [ ] **Commit job discovery docs**

```bash
git add docs/features/job-discovery.md
git commit -m "docs: add job discovery documentation

Integrate scraper plugin design

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 10: Resume Tailoring Feature Documentation

**Files:**
- Create: `docs/features/resume-tailoring.md`

- [ ] **Create resume-tailoring.md**

Content:
- LaTeX workflow (master.tex → tailoring → PDF)
- Agent roles (JobParsingAgent extracts requirements, ResumeTailorAgent rewrites)
- Prompt engineering details
- PDF generation (pdflatex compilation)
- LaTeX validation (pre/post hooks if implemented)
- Common failures (malformed LaTeX, missing packages)
- Customization tips

- [ ] **Commit resume tailoring docs**

```bash
git add docs/features/resume-tailoring.md
git commit -m "docs: add resume tailoring documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 11: Application Tracking Feature Documentation

**Files:**
- Create: `docs/features/application-tracking.md`

- [ ] **Create application-tracking.md**

Content:
- Dashboard usage
- Job status lifecycle (suggested → processing → applied → interviewing/rejected/offer, failed, dismissed)
- Score interpretation (0-100, color coding)
- Filtering and search
- PDF downloads
- Status updates

- [ ] **Commit application tracking docs**

```bash
git add docs/features/application-tracking.md
git commit -m "docs: add application tracking documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 12: Development Guide

**Files:**
- Create: `docs/development/README.md`

- [ ] **Create development/README.md**

Content:
- Local development setup
- Running services separately
- Testing workflow
- Code structure overview
- Contributing guidelines (for future you)
- Links to other development docs

- [ ] **Commit development guide**

```bash
git add docs/development/README.md
git commit -m "docs: add development guide

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 13: Copilot Setup Documentation

**Files:**
- Create: `docs/development/copilot-setup.md`

- [ ] **Create copilot-setup.md**

Content:
- Purpose of CLAUDE.md (AI assistant instructions for Copilot CLI)
- Location (root directory, untouched)
- How Copilot reads it automatically
- Customization guidelines
- Other AI instruction files (GEMINI.md, AGENTS.md if they exist)

- [ ] **Commit Copilot setup docs**

```bash
git add docs/development/copilot-setup.md
git commit -m "docs: add Copilot setup documentation

Document CLAUDE.md purpose and customization

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 14: Database Migrations Documentation

**Files:**
- Create: `docs/development/database-migrations.md`

- [ ] **Create database-migrations.md**

Content:
- Alembic workflow
- Creating migrations (`alembic revision --autogenerate`)
- Running migrations (`alembic upgrade head`)
- Hybrid mode explained (PostgreSQL ↔ SQLite sync)
- Migration best practices
- Troubleshooting migration failures

- [ ] **Commit database migrations docs**

```bash
git add docs/development/database-migrations.md
git commit -m "docs: add database migrations guide

Document Alembic and hybrid mode

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 15: Testing Documentation

**Files:**
- Create: `docs/development/testing.md`

- [ ] **Create testing.md**

Content:
- Agent testing with stub mode (RESUME_TAILOR_LLM_MODE=stub)
- Dry-run testing (when Feature 8 is implemented)
- Testing discovery without API costs
- Manual testing workflow
- Future: unit tests, integration tests

- [ ] **Commit testing docs**

```bash
git add docs/development/testing.md
git commit -m "docs: add testing documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## PHASE 3: Migrate Existing Content

### Task 16: Create Feature Roadmap

**Files:**
- Create: `docs/enhancements/roadmap.md`
- Read: `HARNESS_ENHANCEMENTS.md`

- [ ] **Extract Essential + Very Useful features into roadmap.md**

Content from HARNESS_ENHANCEMENTS.md:
- **Essential** (4 features): Real-Time Streaming Progress (F1), Pre/Post Agent Hooks (F2), Bootstrap Sequence (F9), Timezone Fix (F11)
- **Very Useful** (3 features): Token Usage Tracking (F4), Audit Logging (F7), Dry-Run Mode (F8)
- For each: problem statement, what to build, expected impact
- Organized by priority with clear next steps

- [ ] **Commit roadmap**

```bash
git add docs/enhancements/roadmap.md
git commit -m "docs: create feature roadmap

Extract Essential and Very Useful features from HARNESS_ENHANCEMENTS

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 17: Document Implemented Features

**Files:**
- Create: `docs/enhancements/implemented.md`
- Read: `IMPLEMENTATION_VERIFICATION_REPORT.md`
- Read: `HARNESS_ENHANCEMENTS.md:260-273` (Feature 3 partial implementation)
- Read: `HARNESS_ENHANCEMENTS.md:442-543` (Feature 5 partial implementation)

- [ ] **Consolidate IMPLEMENTATION_VERIFICATION_REPORT + completed features**

Content:
- Feature 0: Shared Frontend API Client (completed)
- Feature 3: Multi-Provider LLM Support (partially implemented - LLMProvider abstraction, GeminiProvider, StubProvider)
- Feature 5: Site-Specific Scraper Plugins (partially implemented - domain manifests for 6 sites)
- Verification status for each
- What works, what's pending

- [ ] **Commit implemented features**

```bash
git add docs/enhancements/implemented.md
git commit -m "docs: document implemented features

Consolidate verification report and completed items

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 18: Archive HARNESS_ENHANCEMENTS.md

**Files:**
- Create: `docs/enhancements/archive/harness-inspiration.md`
- Read: `HARNESS_ENHANCEMENTS.md`

- [ ] **Copy full HARNESS_ENHANCEMENTS.md to archive**

```bash
cp HARNESS_ENHANCEMENTS.md docs/enhancements/archive/harness-inspiration.md
```

- [ ] **Add archive note to top of file**

Add at top of `docs/enhancements/archive/harness-inspiration.md`:

```markdown
> **Archive Note**: This document contains the full original HARNESS_ENHANCEMENTS.md with all 11 proposed features. Essential and Very Useful features were extracted to [roadmap.md](../roadmap.md). This archive preserves the complete design thinking and harness inspirations for historical reference.

---

```

- [ ] **Commit archived harness doc**

```bash
git add docs/enhancements/archive/harness-inspiration.md
git commit -m "docs: archive full HARNESS_ENHANCEMENTS document

Preserve original harness-inspired designs for reference

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 19: Move API Specifications

**Files:**
- Move: `backend/services/resume-tailor/spec.md` → `docs/api/resume-tailor-api.md`

- [ ] **Move resume-tailor spec to docs/api/**

```bash
git mv backend/services/resume-tailor/spec.md docs/api/resume-tailor-api.md
```

- [ ] **Commit API spec move**

```bash
git commit -m "docs: move resume-tailor API spec to docs/api/

Relocate from backend/ for better discoverability

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 20: Create Scraper API Documentation

**Files:**
- Create: `docs/api/scraper-api.md`
- Read: `backend/services/job-scraper/main.py`

- [ ] **Document scraper API from main.py**

Content:
- POST /scrape endpoint
- Request schema (url: str, wait_time: int = 3)
- Response schema (html: str, error: Optional[str])
- Example usage with curl
- Playwright configuration

- [ ] **Commit scraper API docs**

```bash
git add docs/api/scraper-api.md
git commit -m "docs: add scraper API documentation

Document POST /scrape endpoint and usage

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## PHASE 4: Simplify Root and Service READMEs

### Task 21: Simplify Root README

**Files:**
- Modify: `README.md`

- [ ] **Replace README.md with concise landing page**

New content (~40 lines):
- Hero: "AutoCareer - Self-hosted job automation with AI"
- Key features (4 bullets): AI Job Discovery, Smart Scoring, Resume Tailoring, Application Tracking
- Quick start (5 steps): Clone → Configure → Add Resume → Start Services → Open UI
- Documentation link: "See [docs/](./docs/) for complete documentation"
- Technology badges (optional)

- [ ] **Commit simplified README**

```bash
git add README.md
git commit -m "docs: simplify root README to landing page

Focus on quick value, link to docs/ for details

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 22: Simplify Backend READMEs

**Files:**
- Modify: `backend/services/resume-tailor/README.md`
- Modify: `backend/services/job-scraper/README.md`

- [ ] **Simplify resume-tailor README**

Replace with:
```markdown
# Resume Tailor Service

The core backend service for AutoCareer - handles AI job discovery, scoring, and resume tailoring.

📚 **Full documentation**: See [docs/](../../../docs/)

## Quick Development Setup

\`\`\`bash
cd backend/services/resume-tailor
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
\`\`\`
```

- [ ] **Simplify job-scraper README**

Replace with:
```markdown
# Job Scraper Service

Headless browser service for fetching job pages using Playwright.

📚 **Full documentation**: See [docs/](../../../docs/)

## Quick Development Setup

\`\`\`bash
cd backend/services/job-scraper
pip install -r requirements.txt
uvicorn main:app --reload --port 8001
\`\`\`
```

- [ ] **Commit simplified backend READMEs**

```bash
git add backend/services/resume-tailor/README.md backend/services/job-scraper/README.md
git commit -m "docs: simplify backend service READMEs

Convert to pointers to main documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 23: Simplify Frontend README

**Files:**
- Modify: `frontend/README.md`

- [ ] **Simplify frontend README**

Replace with:
```markdown
# AutoCareer Frontend

Web interface for AutoCareer - built with Next.js 14, TypeScript, and shadcn/ui.

📚 **Full documentation**: See [docs/](../docs/)

## Quick Development Setup

\`\`\`bash
cd frontend
npm install
npm run dev
\`\`\`

Open [http://localhost:3000](http://localhost:3000) in your browser.
```

- [ ] **Commit simplified frontend README**

```bash
git add frontend/README.md
git commit -m "docs: simplify frontend README

Convert to pointer to main documentation

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 24: Delete Consolidated Files

**Files:**
- Delete: `PROJECT_README.md`
- Delete: `FolderStruct.md`
- Delete: `HARNESS_ENHANCEMENTS.md`
- Delete: `IMPLEMENTATION_VERIFICATION_REPORT.md`
- Delete: `SCRAPER_PLUGIN_DESIGN_DOC.md`
- Delete: `backend/services/resume-tailor/QUICKSTART.md`

- [ ] **Remove consolidated documentation files**

```bash
git rm PROJECT_README.md
git rm FolderStruct.md
git rm HARNESS_ENHANCEMENTS.md
git rm IMPLEMENTATION_VERIFICATION_REPORT.md
git rm SCRAPER_PLUGIN_DESIGN_DOC.md
git rm backend/services/resume-tailor/QUICKSTART.md
```

- [ ] **Verify root is clean**

```bash
ls -1 *.md *.todo
```

Expected: Only README.md, CLAUDE.md, TODO.todo

- [ ] **Commit cleanup**

```bash
git commit -m "docs: remove consolidated documentation files

Content migrated to docs/:
- PROJECT_README → docs/architecture/overview.md
- FolderStruct → docs/architecture/overview.md
- HARNESS_ENHANCEMENTS → docs/enhancements/roadmap.md + archive/
- IMPLEMENTATION_VERIFICATION_REPORT → docs/enhancements/implemented.md
- SCRAPER_PLUGIN_DESIGN_DOC → docs/features/job-discovery.md
- backend QUICKSTART → docs/getting-started/quickstart.md

Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

---

## PHASE 5: Verification

### Task 25: Verify Documentation Structure

**Files:**
- All documentation in `docs/`

- [ ] **Check all documents exist**

```bash
cd /Users/alexyuan/Documents/job-auto-apply
find docs -name "*.md" | sort
```

Expected minimum 18 files:
- docs/README.md
- docs/getting-started/quickstart.md
- docs/getting-started/environment-setup.md
- docs/getting-started/deployment.md
- docs/architecture/overview.md
- docs/architecture/data-flow.md
- docs/architecture/technology-stack.md
- docs/features/job-discovery.md
- docs/features/resume-tailoring.md
- docs/features/application-tracking.md
- docs/development/README.md
- docs/development/copilot-setup.md
- docs/development/database-migrations.md
- docs/development/testing.md
- docs/enhancements/roadmap.md
- docs/enhancements/implemented.md
- docs/enhancements/archive/harness-inspiration.md
- docs/api/resume-tailor-api.md
- docs/api/scraper-api.md
- Plus specs and plans

- [ ] **Verify root is clean**

```bash
ls -1 *.md *.todo
```

Expected exactly 3 files:
- README.md
- CLAUDE.md
- TODO.todo

- [ ] **Check for broken links**

Search for common link patterns:

```bash
grep -r "]\(./" docs/ | grep -v "\.md:"
```

Should return empty (no broken relative links)

- [ ] **Final verification report**

Create checklist:
1. ✅ New user can find quickstart from root README in <10 seconds
2. ✅ Root directory has ≤5 markdown files
3. ✅ All features categorized (Essential/Useful/Nice/Skip) in roadmap
4. ✅ CLAUDE.md untouched in root
5. ✅ Backend/frontend READMEs are pointers
6. ✅ No broken links
7. ✅ Clear navigation from docs/README.md

---

## Success Criteria (From Spec)

After completion, verify all 7 success criteria:

1. **✅ New user can find quickstart in under 10 seconds**
   - Root README has "See docs/" link
   - docs/README.md has "New Here? Start Here!" with quickstart link

2. **✅ Root directory has 5 or fewer markdown files**
   - Count: README.md, CLAUDE.md (3 with TODO.todo)

3. **✅ All features are categorized by priority**
   - docs/enhancements/roadmap.md has Essential, Very Useful sections

4. **✅ AI instruction files remain untouched**
   - CLAUDE.md in root, documented in docs/development/copilot-setup.md

5. **✅ Backend/frontend READMEs point to main docs**
   - All service READMEs have "Full documentation: See docs/"

6. **✅ No broken links**
   - All markdown links verified

7. **✅ Clear navigation from docs/README.md**
   - docs/README.md has complete section index

## Execution Notes

**Total tasks**: 25 (includes verification)

**Estimated time**: 3-4 hours

**Dependencies**: None - pure documentation work

**Testing**: New user starts at README.md → clicks docs/ → finds quickstart in "New Here? Start Here!"

**Commit strategy**: One commit per task (25 commits total)

