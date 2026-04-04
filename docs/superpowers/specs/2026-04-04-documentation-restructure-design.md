# Documentation Restructure and Feature Prioritization Design

**Date:** 2026-04-04  
**Status:** Approved  
**Goal:** Establish clean documentation structure and prioritize HARNESS_ENHANCEMENTS.md features for production use

## Background

AutoCareer is a self-hosted job automation platform currently in active development with 7 root-level markdown files, scattered documentation across backend/frontend, and a 985-line HARNESS_ENHANCEMENTS.md containing 11 proposed features. The project goal is a production-ready personal tool (single-user) for actual job searching.

### Current State Problems

1. **Documentation chaos**: 7 MD files in root (README, PROJECT_README, FolderStruct, CLAUDE, HARNESS_ENHANCEMENTS, IMPLEMENTATION_VERIFICATION_REPORT, SCRAPER_PLUGIN_DESIGN_DOC)
2. **Unclear priorities**: HARNESS_ENHANCEMENTS.md contains both essential features and speculative optimizations
3. **Duplication**: README, PROJECT_README, and FolderStruct overlap significantly
4. **Poor discoverability**: New user doesn't know where to start

## Goals

1. Create single `docs/` directory with clear organization
2. Identify essential vs. nice-to-have features for single-user production use
3. Maintain root-level AI instruction files (CLAUDE.md) untouched
4. Simplify backend/frontend READMEs to pointers
5. Archive planning documents while preserving historical context

## Feature Prioritization

From HARNESS_ENHANCEMENTS.md's 11 features:

### Essential (Must Have for Production)

1. **Feature 1: Real-Time Streaming Progress via SSE** - Users need visibility during long operations (10-30 second resume tailoring)
2. **Feature 2: Pre/Post Agent Hooks for Quality Control** - Currently #1 failure mode is broken LaTeX output
3. **Feature 9: Bootstrap Sequence and Startup Health Checks** - Catch missing API keys before wasting time
4. **Feature 11: Timezone-Aware Date Handling** - Small bug causing wrong date groupings in dashboard

### Very Useful (Should Have Soon)

5. **Feature 4: Token Usage Tracking and Cost Dashboard** - Monitor API costs with daily scans
6. **Feature 7: Conversation/Audit Logging per Job Application** - Debug failed applications
7. **Feature 8: Dry-Run / Safe-Scan Permission Mode** - Test before burning API credits

### Nice to Have (Future)

8. **Feature 3: Multi-Provider LLM Support** - Fallback if Gemini is down (partially implemented)
9. **Feature 5: Site-Specific Scraper Plugins** - More job sites (partially implemented)
10. **Feature 6: Structured System Prompt Builder** - Tweaking prompts for better results

### Probably Skip

11. **Feature 10: Session Compaction for Long Job Descriptions** - Premature optimization, only needed for extremely long descriptions

## Documentation Structure

### New Directory Layout

```
docs/
├── README.md                           # Navigation hub - "start here" guide
├── getting-started/
│   ├── quickstart.md                   # Consolidate setup from multiple sources
│   ├── environment-setup.md            # Detailed env var explanations
│   └── deployment.md                   # Docker setup, common issues, health checks
├── architecture/
│   ├── overview.md                     # Merge PROJECT_README + FolderStruct
│   ├── data-flow.md                    # Job discovery → scoring → tailoring workflow
│   └── technology-stack.md             # Why each tech choice
├── features/
│   ├── job-discovery.md                # AI discovery, scraper plugins, source config
│   ├── resume-tailoring.md             # LaTeX workflow, agent prompts, PDF generation
│   └── application-tracking.md         # Dashboard, status lifecycle, score interpretation
├── development/
│   ├── README.md                       # Overview for contributors
│   ├── copilot-setup.md                # Purpose of CLAUDE.md and customization
│   ├── database-migrations.md          # Alembic workflow, hybrid mode explained
│   └── testing.md                      # Agent testing, stub mode, dry-run
├── enhancements/
│   ├── roadmap.md                      # Essential + Very Useful features prioritized
│   ├── implemented.md                  # Consolidate verification report + completed features
│   └── archive/
│       └── harness-inspiration.md      # Full HARNESS_ENHANCEMENTS.md for reference
└── api/
    ├── resume-tailor-api.md            # Based on backend spec.md
    └── scraper-api.md                  # Scraper service API
```

### Root Level After Restructure

```
/job-auto-apply/
├── README.md                           # GitHub landing page (simplified)
├── CLAUDE.md                           # AI assistant instructions (UNTOUCHED)
├── TODO.todo                           # Working task list (UNTOUCHED)
├── docs/                               # All consolidated documentation
├── backend/
│   ├── services/
│   │   ├── resume-tailor/
│   │   │   └── README.md              # Minimal pointer to docs/
│   │   └── job-scraper/
│   │       └── README.md              # Minimal pointer to docs/
├── frontend/
│   └── README.md                       # Minimal pointer to docs/
├── docker-compose.yml
└── package.json
```

## Migration Plan

### Files to Move/Transform

| Current File | Destination | Action |
|-------------|-------------|--------|
| `README.md` | Keep in root | Simplify to 5-step quickstart + link to docs/ |
| `PROJECT_README.md` | `docs/architecture/overview.md` | Merge with FolderStruct |
| `FolderStruct.md` | `docs/architecture/overview.md` | Merge with PROJECT_README |
| `CLAUDE.md` | Root (untouched) | Document purpose in `docs/development/copilot-setup.md` |
| `HARNESS_ENHANCEMENTS.md` | Split: `docs/enhancements/roadmap.md` + `docs/enhancements/archive/harness-inspiration.md` | Extract prioritized features to roadmap, archive full doc |
| `IMPLEMENTATION_VERIFICATION_REPORT.md` | `docs/enhancements/implemented.md` | Move and consolidate with completed features |
| `SCRAPER_PLUGIN_DESIGN_DOC.md` | `docs/features/job-discovery.md` | Integrate into job discovery documentation |
| `TODO.todo` | Root (untouched) | Keep as working task list |
| `backend/services/resume-tailor/README.md` | Simplify in place | Keep 2-3 sentence description + "see docs/" pointer |
| `backend/services/resume-tailor/QUICKSTART.md` | Merge to `docs/getting-started/quickstart.md` | Consolidate all setup instructions |
| `backend/services/resume-tailor/spec.md` | Move to `docs/api/resume-tailor-api.md` | Relocate API reference |
| `backend/services/job-scraper/README.md` | Simplify in place | Keep 2-3 sentence description + "see docs/" pointer |
| `frontend/README.md` | Simplify in place | Keep 2-3 sentence description + "see docs/" pointer |

### New Documents to Create

**Getting Started:**
- `docs/getting-started/quickstart.md` - One command to running system
- `docs/getting-started/environment-setup.md` - Every env var explained with examples
- `docs/getting-started/deployment.md` - Docker setup, troubleshooting, health checks

**Architecture:**
- `docs/architecture/overview.md` - System design, services, interactions
- `docs/architecture/data-flow.md` - Detailed workflow diagrams (text-based)
- `docs/architecture/technology-stack.md` - Tech choices and rationale

**Features:**
- `docs/features/job-discovery.md` - How discovery works, scraper plugins, domain manifests
- `docs/features/resume-tailoring.md` - LaTeX pipeline, agent prompts, PDF generation
- `docs/features/application-tracking.md` - Dashboard usage, status meanings, score interpretation

**Development:**
- `docs/development/README.md` - Contributor overview
- `docs/development/copilot-setup.md` - CLAUDE.md purpose and customization guide
- `docs/development/database-migrations.md` - Alembic workflow, hybrid PostgreSQL/SQLite mode
- `docs/development/testing.md` - Testing agents, stub mode, dry-run testing

**Enhancements:**
- `docs/enhancements/roadmap.md` - Prioritized features (Essential + Very Useful)
- `docs/enhancements/implemented.md` - What's done, what works, verification status

**API:**
- `docs/api/resume-tailor-api.md` - All endpoints with examples
- `docs/api/scraper-api.md` - Scraper service API

**Navigation:**
- `docs/README.md` - Quick links to all sections, "new user start here" guide

## Root README Redesign

The root `README.md` will become a concise landing page:

1. **Hero section**: Project tagline, key features (4 bullet points)
2. **Quick start**: 5 steps from clone to running UI
3. **Documentation link**: "See [docs/](./docs/) for complete documentation"
4. **Technology badges**: Next.js, Python, FastAPI, PostgreSQL, Docker

**Current:** 152 lines mixing quickstart, architecture, features, usage  
**Target:** ~40 lines focused on immediate value

## Service README Simplification

**Backend/frontend READMEs become 3-sentence pointers:**

```markdown
# Resume Tailor Service

The core backend service for AutoCareer - handles AI job discovery, scoring, and resume tailoring.

📚 **Full documentation**: See [docs/](../../docs/)

## Quick Development Setup

\`\`\`bash
cd backend/services/resume-tailor
pip install -r requirements.txt
uvicorn server:app --reload --port 8000
\`\`\`
```

## Implementation Approach

### Phase 1: Create Structure (No Migration)

1. Create `docs/` directory with all subdirectories
2. Create `docs/README.md` navigation hub
3. Git commit: "Create documentation structure"

### Phase 2: Write New Content

1. Write all new documents (getting-started/, architecture/, features/, development/, api/)
2. Focus on filling gaps, not duplicating existing content yet
3. Git commit per section: "Add getting-started documentation", etc.

### Phase 3: Migrate and Consolidate

1. Extract content from root-level files into appropriate docs/
2. Archive HARNESS_ENHANCEMENTS.md to docs/enhancements/archive/
3. Create prioritized roadmap from HARNESS features
4. Move API specs from backend/ to docs/api/
5. Git commit: "Migrate existing documentation to docs/"

### Phase 4: Simplify Root and Services

1. Simplify root README.md to landing page
2. Simplify backend/frontend READMEs to pointers
3. Delete consolidated files: PROJECT_README.md, FolderStruct.md, HARNESS_ENHANCEMENTS.md, IMPLEMENTATION_VERIFICATION_REPORT.md, SCRAPER_PLUGIN_DESIGN_DOC.md
4. Git commit: "Clean up root directory and simplify service READMEs"

### Phase 5: Document AI Instructions

1. Create `docs/development/copilot-setup.md` explaining CLAUDE.md purpose
2. Reference it from development/README.md
3. Git commit: "Document AI assistant setup"

## Success Criteria

1. ✅ New user can find quickstart in under 10 seconds
2. ✅ Root directory has 5 or fewer markdown files
3. ✅ All features are categorized by priority (Essential/Useful/Nice/Skip)
4. ✅ AI instruction files (CLAUDE.md) remain untouched in root
5. ✅ Backend/frontend READMEs point to main docs instead of duplicating
6. ✅ No broken links between documents
7. ✅ Clear navigation from docs/README.md to any topic

## Non-Goals

- Implement any HARNESS features (this is planning only)
- Change code structure or architecture
- Modify AI instruction files
- Create visual diagrams (text-based descriptions sufficient)
- Set up documentation generation tools (manual markdown is fine)

## Open Questions

None - design approved.
