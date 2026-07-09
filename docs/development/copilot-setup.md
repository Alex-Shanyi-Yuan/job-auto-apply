# Copilot & AI Assistant Setup

This document explains how AI coding assistants (GitHub Copilot CLI, Claude Code) are configured to work effectively with the AutoCareer codebase.

## Overview

The AutoCareer repository includes instruction files that provide context and guidelines to AI assistants. These files help AI understand the project architecture, development workflows, and coding patterns.

## Instruction Files

### `CLAUDE.md` (Primary)

**Location:** Repository root (`/Users/alexyuan/Documents/job-auto-apply/CLAUDE.md`)

**Purpose:**
- Provides comprehensive context to GitHub Copilot CLI and Claude Code
- Documents development commands, architecture, and workflows
- Serves as the single source of truth for AI assistant configuration

**When It's Read:**
- Automatically loaded by GitHub Copilot CLI in every session
- Read by Claude Code when working in this repository
- Never needs manual inclusion — AI assistants discover it automatically

**Content Includes:**
- Development commands (docker-compose, npm, alembic)
- Service architecture and port mappings
- Key source file locations
- Frontend and backend patterns
- Environment variable reference
- Testing notes and gotchas

**⚠️ Important:**
- **Never move or rename** this file — AI assistants expect it at the root
- **Never delete** — it's critical for AI assistant functionality
- **Always update** when making architectural changes

### Other AI Instruction Files

**`.github/copilot-instructions.md`**
- Thin pointer at CLAUDE.md for GitHub Copilot, plus a few essentials
- **Never add project knowledge there** — CLAUDE.md is the single canonical instruction file

**`.claude/settings.json` + `.claude/hooks/check-docs-sync.sh`**
- Project-level Claude Code config: a `Stop` hook that reminds the session to update docs when code changed but no `docs/`/CLAUDE.md files did (part of the Knowledge Retention Policy)

## How GitHub Copilot CLI Uses CLAUDE.md

The GitHub Copilot CLI (the agent you're talking to) automatically reads CLAUDE.md as a **custom instruction** file. This means:

1. **Context Loading:** Every session starts with knowledge from CLAUDE.md
2. **Command Awareness:** Copilot knows how to run, test, and debug your code
3. **Pattern Matching:** Copilot follows established architectural patterns
4. **Best Practices:** Copilot applies project-specific conventions

**Example Workflow:**
```
You: "Add a new API endpoint for job search"

Copilot (using CLAUDE.md context):
1. Adds endpoint to server.py (knows location)
2. Adds typed client function to frontend/lib/api.ts (knows pattern)
3. Suggests testing with curl (knows commands)
4. Reminds about database migration if schema changes (knows workflow)
```

## How Claude Code Uses CLAUDE.md

When working in `claude.ai/code`:

1. Claude automatically detects and reads CLAUDE.md
2. Uses it to understand project structure
3. Applies documented patterns to code generation
4. Follows development commands for testing

**No manual upload needed** — Claude finds and reads the file automatically.

## Customization Guidelines

### When to Update CLAUDE.md

The authoritative rules live in CLAUDE.md itself — see its **"Knowledge Retention Policy"** and **"Documentation Map"** sections at the top of the file. In short: documentation updates ship in the same commit as the code change, and the map tells you exactly which doc corresponds to which code area. This section is intentionally not duplicated here.

### How to Update CLAUDE.md

1. **Open the file:**
   ```bash
   code CLAUDE.md  # or vim, nano, etc.
   ```

2. **Make focused changes:**
   - Keep development commands accurate
   - Update service port mappings if changed
   - Add new key source files
   - Document new environment variables

3. **Keep it concise:**
   - Focus on what AI needs to write code effectively
   - Avoid redundant information already in documentation
   - Use tables and code blocks for clarity

4. **Test the changes:**
   - Ask Copilot a question about the updated area
   - Verify it uses the new information correctly

### What NOT to Put in CLAUDE.md

- ❌ Detailed API documentation (use OpenAPI/Swagger instead)
- ❌ User guides (put in `docs/`)
- ❌ Long explanations (keep it reference-style)
- ❌ Sensitive data (API keys, credentials)
- ❌ Temporary notes (use session-specific files)

## Best Practices for Working with AI Assistants

### 1. Be Specific in Prompts

**❌ Vague:**
> "Fix the frontend"

**✅ Clear:**
> "In frontend/app/suggestions/page.tsx, fix the scan status polling to handle network errors gracefully"

### 2. Reference Documented Patterns

**❌ Unclear:**
> "Add a database query"

**✅ Pattern-Aware:**
> "Add a database query following the session pattern from database.py (with Session(engine) as session)"

### 3. Mention Relevant Context Files

When asking about architecture:
> "According to CLAUDE.md, what's the service architecture?"

When asking about development:
> "What's the recommended way to run the frontend locally? (Check CLAUDE.md)"

### 4. Request Documentation Updates

After making changes:
> "Update CLAUDE.md to reflect the new port mapping for the analytics service"

### 5. Test AI-Generated Code

Always verify:
- [ ] Code runs without errors
- [ ] Follows project patterns (check CLAUDE.md)
- [ ] Environment variables are documented
- [ ] Database migrations created if needed

### 6. Use Stub Mode for AI Feature Testing

When developing or debugging AI agents:
```bash
RESUME_TAILOR_LLM_MODE=stub uvicorn server:app --reload
```

This allows testing agent logic without API costs. See [Testing Strategies](./testing.md).

## Common AI-Assisted Workflows

### Adding a Feature

1. **Describe the feature clearly:**
   > "Add a job export feature that downloads all applied jobs as a CSV file"

2. **Let AI propose the approach:**
   > AI will reference CLAUDE.md to know:
   > - Where to add the endpoint (server.py)
   > - How to add the frontend button (shadcn/ui patterns)
   > - Which database model to query (database.py)

3. **Review and iterate:**
   > "Use the Job model from database.py and add a download button to the dashboard page"

### Debugging with AI

1. **Provide error context:**
   > "I'm getting a 500 error on POST /suggestions/refresh. Here's the traceback: [paste error]"

2. **AI will check known issues:**
   > AI references CLAUDE.md testing notes and common gotchas

3. **Implement fix:**
   > AI proposes fix based on documented patterns

### Refactoring with AI

1. **State the goal:**
   > "Refactor the job discovery scan to use asyncio instead of ThreadPoolExecutor"

2. **AI uses architectural knowledge:**
   > - Knows current implementation (from CLAUDE.md patterns)
   > - Suggests async/await pattern
   > - Updates affected endpoints

3. **Verify no regressions:**
   > "Run the discovery scan test to ensure it still works"

## Troubleshooting AI Assistant Behavior

### AI suggests wrong file paths

**Cause:** CLAUDE.md may be outdated  
**Fix:** Update key source file locations in CLAUDE.md

### AI uses deprecated patterns

**Cause:** Old patterns still documented  
**Fix:** Update code patterns section in CLAUDE.md

### AI doesn't know about new features

**Cause:** CLAUDE.md not updated after feature addition  
**Fix:** Add new service/endpoint/model to CLAUDE.md

### AI suggests incorrect commands

**Cause:** Development commands section outdated  
**Fix:** Update commands in CLAUDE.md and test them

## Maintaining CLAUDE.md Over Time

Maintenance rules are defined in CLAUDE.md's **"Knowledge Retention Policy"** — update CLAUDE.md and the mapped `docs/` files in the same commit as the code change, and grep `docs/` for terms your change made obsolete. Enforcement: the `Stop` hook in `.claude/settings.json` reminds any Claude Code session that changed code without touching docs.

## AI Assistant Limitations

Even with CLAUDE.md, AI assistants:

- ❌ Cannot run arbitrary shell commands without permission
- ❌ Cannot access external services (databases, APIs) directly
- ❌ May hallucinate details not in context
- ❌ Cannot read your mind — be explicit in requests

**Always verify AI-generated code** before committing.

## Example: CLAUDE.md Anatomy

Here's what a well-structured CLAUDE.md contains:

```markdown
# CLAUDE.md

## Development Commands
[Frequently used commands for running, testing, building]

## Architecture
[Service overview, port mappings, tech stack]

## Key Source Files
[Critical files with descriptions]

## Database Schema
[Table structures, relationships]

## API Endpoints
[Grouped by feature with HTTP methods]

## AI Agents
[Agent descriptions, input/output schemas]

## Key Workflows
[Step-by-step process flows]

## Frontend Patterns
[React patterns, state management, API calls]

## Backend Patterns
[FastAPI patterns, database sessions, background tasks]

## Environment Variables
[Required and optional env vars with defaults]

## Testing Notes
[Gotchas, known issues, testing tips]
```

## Additional Resources

- [Development Guide](./README.md) — Local setup and workflows
- [Testing Strategies](./testing.md) — AI agent testing
- [Database Migrations](./database-migrations.md) — Schema changes

## Questions?

Since you're reading this, you're likely your own collaborator. If this setup stops working:

1. Check that CLAUDE.md exists at repository root
2. Verify it contains accurate development commands
3. Ask Copilot: "What do you know about this codebase from CLAUDE.md?"
4. Update CLAUDE.md if information is stale
