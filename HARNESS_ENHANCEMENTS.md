# Harness-Inspired Enhancement Plan for AutoCareer

This document maps concepts from the Claw Code Harness (`claw-code-main`) to concrete, actionable improvements for the AutoCareer job-auto-apply platform. Each feature is grounded in current code gaps and includes specific file targets, action items, and expected impact.

---

## How to Read This Document

- **Impact** = how much the feature improves the user experience or system reliability
- **Effort** = implementation complexity (Small / Medium / Large)
- **Priority** = recommended build order (1 = do first)
- Action items reference exact files so you can start immediately

---

## Feature 1: Real-Time Streaming Progress via Server-Sent Events

**Priority: 1 | Impact: High | Effort: Medium**

### Problem (Current State)

The frontend polls `GET /suggestions/status` every 1.5 seconds and `GET /jobs/{id}` every 2 seconds during resume tailoring. This is inefficient and introduces latency. Long-running resume tailoring (~10–30 seconds) shows no step-by-step progress. The resume compilation step completely blocks the backend uvicorn event loop (`server.py` line 302: `await asyncio.to_thread(compile_pdf, ...)`).

### Harness Concept Applied

The harness streams `AssistantEvent` tokens from the API client (`conversation.rs` §2), giving real-time feedback for each step in the pipeline. The `ConversationRuntime::run_turn()` pushes deltas to the caller as they arrive rather than waiting for the full response.

### What to Build

**Backend:** Add a `GET /jobs/{job_id}/stream` SSE endpoint that emits pipeline step events as the background task progresses.

**Frontend:** Replace the 2-second polling interval on `jobs/[id]/page.tsx` with an `EventSource` connection to the stream endpoint.

### Actionable Items

1. **Add pipeline event bus** — Create `backend/services/resume-tailor/core/events.py`:
   ```python
   # Per-job asyncio.Queue for pipeline step events
   job_event_queues: dict[int, asyncio.Queue] = {}
   
   async def emit(job_id: int, step: str, detail: str = ""):
       if job_id in job_event_queues:
           await job_event_queues[job_id].put({"step": step, "detail": detail})
   ```

2. **Instrument `process_application()`** in `server.py` (lines 255–320) — call `emit()` at each step:
   - After scrape complete: `"scraping_complete"`
   - After parse complete: `"parsing_complete"`
   - After tailoring starts: `"tailoring_started"`
   - After tailoring complete: `"tailoring_complete"`
   - After PDF compiled: `"pdf_compiled"`
   - On error: `"failed"`

3. **Add SSE route** in `server.py`:
   ```python
   @app.get("/jobs/{job_id}/stream")
   async def stream_job_progress(job_id: int):
       queue = asyncio.Queue()
       job_event_queues[job_id] = queue
       async def generator():
           while True:
               event = await asyncio.wait_for(queue.get(), timeout=60)
               yield f"data: {json.dumps(event)}\n\n"
               if event["step"] in ("pdf_compiled", "failed"):
                   break
       return StreamingResponse(generator(), media_type="text/event-stream")
   ```

4. **Update `jobs/[id]/page.tsx`** — Replace `setInterval` polling with `EventSource`:
   ```typescript
   const es = new EventSource(`${API_BASE}/jobs/${id}/stream`);
   es.onmessage = (e) => {
     const event = JSON.parse(e.data);
     setCurrentStep(event.step);
     if (event.step === 'pdf_compiled' || event.step === 'failed') {
       es.close();
       loadJob();
     }
   };
   ```

5. **Add step labels to UI** — Show `"Analyzing job requirements..."`, `"Rewriting resume bullet points..."`, `"Compiling PDF..."` as progress steps.

6. **Add `lib/api.ts`** helper: `streamJobProgress(jobId, onStep)`.

### Files to Modify
- `backend/services/resume-tailor/server.py` (lines 255–320, plus new route)
- `backend/services/resume-tailor/core/` (new `events.py`)
- `frontend/app/jobs/[id]/page.tsx`
- `frontend/lib/api.ts`

### Expected Impact
- Eliminates 2-second polling lag on the most user-facing flow
- Makes resume tailoring feel responsive (users see "Analyzing requirements..." in <1s)
- Removes the only busy-wait loop that currently blocks UX feedback
- Unblocks the apply button — users know exactly where in the pipeline their job is

---

## Feature 2: Pre/Post Agent Hooks for Quality Control

**Priority: 2 | Impact: High | Effort: Medium**

### Problem (Current State)

The 4 AI agents (`agents.py`) execute with no pre/post interception. LaTeX validation only checks for 3 structure strings (`\documentclass`, `\begin{document}`, `\end{document}`). If the LLM hallucinates broken LaTeX, the PDF compilation fails and the job lands in `status="failed"` with a cryptic error. There is no way to add monitoring, logging, or quality gates without modifying agent code directly.

### Harness Concept Applied

The harness runs `hook_runner.run_pre_tool_use()` before every tool call and `hook_runner.run_post_tool_use()` after. Exit code 2 from a hook denies the tool call entirely. This gives a clean interception point without touching tool logic. The `HookRunResult` carries messages that are appended to the tool result for transparency.

### What to Build

Add a lightweight hook system to the agent pipeline: pre-call hooks validate inputs, post-call hooks validate and optionally repair outputs. Hooks are Python callables registered in a registry, not shell commands (adapting the concept to Python).

### Actionable Items

1. **Create `backend/services/resume-tailor/core/hooks.py`**:
   ```python
   from enum import Enum
   from dataclasses import dataclass
   from typing import Callable, Optional
   
   class HookOutcome(Enum):
       ALLOW = "allow"
       DENY  = "deny"
       WARN  = "warn"
   
   @dataclass
   class HookResult:
       outcome: HookOutcome
       message: str = ""
   
   # Hook signature: (agent_name, input_data) -> HookResult
   PreHook  = Callable[[str, dict], HookResult]
   PostHook = Callable[[str, dict, str], HookResult]  # name, input, output
   
   class AgentHookRunner:
       def __init__(self):
           self._pre: list[PreHook] = []
           self._post: list[PostHook] = []
   
       def register_pre(self, hook: PreHook): self._pre.append(hook)
       def register_post(self, hook: PostHook): self._post.append(hook)
   
       def run_pre(self, agent: str, input_data: dict) -> HookResult:
           for hook in self._pre:
               result = hook(agent, input_data)
               if result.outcome == HookOutcome.DENY:
                   return result
           return HookResult(HookOutcome.ALLOW)
   
       def run_post(self, agent: str, input_data: dict, output: str) -> HookResult:
           for hook in self._post:
               result = hook(agent, input_data, output)
               if result.outcome == HookOutcome.DENY:
                   return result
           return HookResult(HookOutcome.ALLOW)
   ```

2. **Register built-in quality hooks** in `server.py` startup:
   - **Pre-hook: `validate_resume_latex_input`** — verify `master.tex` loads without syntax errors before passing to `ResumeTailorAgent`
   - **Post-hook: `validate_tailored_latex`** — stronger validation: check for common LLM LaTeX mistakes (unclosed braces, markdown fences in LaTeX, missing `\end{document}`)
   - **Post-hook: `log_agent_output`** — write agent name + truncated output to a structured log for debugging

3. **Wrap agent calls in `process_application()`** (`server.py` lines 283–305):
   ```python
   pre = hook_runner.run_pre("ResumeTailorAgent", {"job_title": job.title})
   if pre.outcome == HookOutcome.DENY:
       raise ValueError(f"Pre-hook blocked: {pre.message}")
   tailored = await asyncio.to_thread(tailor_agent.tailor, master_resume, job_posting)
   post = hook_runner.run_post("ResumeTailorAgent", {}, tailored)
   if post.outcome == HookOutcome.DENY:
       raise ValueError(f"Post-hook validation failed: {post.message}")
   ```

4. **Add a `WarnOnLowScore` post-hook** for `JobScoringAgent` — when score < 30 log a warning to the job's `error_message` field so it surfaces in the UI.

5. **Expose hook registration in settings** (future): allow users to add custom Python hook scripts from the UI.

### Files to Modify
- `backend/services/resume-tailor/core/` (new `hooks.py`)
- `backend/services/resume-tailor/server.py` (lines 255–320)
- `backend/services/resume-tailor/core/agents.py`

### Expected Impact
- Reduces `status="failed"` jobs caused by bad LaTeX output (currently the #1 failure mode)
- Adds observability to every agent call — debugging becomes possible without reading logs line by line
- Provides an extension point for custom validation without touching agent logic
- Addresses TODO: "resume tailor logic make it based on json experience based structure" — a post-hook can validate the structure

---

## Feature 3: Multi-Provider LLM Support (Gemini + OpenAI + Claude)

**Priority: 3 | Impact: High | Effort: Medium**

### Problem (Current State)

`llm_client.py` hardcodes `gemini-3-flash-preview` (line 38) and only supports Google Gemini via the `google-genai` library. If the Gemini API is down, the entire platform stops. Different agents have different needs — scoring should be cheap/fast (Haiku-class), tailoring should be best quality (Sonnet/Opus-class). There is no way to assign different models to different agents (TODO item #1 in `TODO.todo`).

### Harness Concept Applied

The harness `ProviderKind` enum (`providers/mod.rs` §15) abstracts over `ClawApi`, `Xai`, and `OpenAi`. The `MODEL_REGISTRY` maps short aliases (`opus`, `sonnet`, `haiku`) to canonical model IDs and auth env vars. `detect_provider_kind()` auto-selects based on available env vars. The `ApiClient` trait is the seam — `ConversationRuntime` never references a specific provider.

### What to Build

Abstract `GeminiClient` behind an `LLMProvider` interface. Add `ClaudeProvider` and `OpenAIProvider`. Allow per-agent model selection via config.

### Actionable Items

1. **Create `backend/services/resume-tailor/core/llm_providers.py`**:
   ```python
   from abc import ABC, abstractmethod
   from typing import Type, TypeVar
   T = TypeVar("T")
   
   class LLMProvider(ABC):
       @abstractmethod
       def generate_text(self, prompt: str, temperature: float = 0.7) -> str: ...
       @abstractmethod
       def generate_structured(self, prompt: str, schema: Type[T], temperature: float = 0.1) -> T: ...
   
   class GeminiProvider(LLMProvider): ...   # extract from llm_client.py
   class ClaudeProvider(LLMProvider): ...   # new: uses anthropic SDK
   class OpenAIProvider(LLMProvider): ...   # new: uses openai SDK
   ```

2. **Add a `MODEL_REGISTRY` dict** (mirrors the harness's `MODEL_REGISTRY`):
   ```python
   MODEL_REGISTRY = {
       "gemini-flash": {"provider": "gemini", "model_id": "gemini-2.0-flash-exp"},
       "gemini-pro":   {"provider": "gemini", "model_id": "gemini-1.5-pro"},
       "haiku":        {"provider": "claude", "model_id": "claude-haiku-4-5-20251001"},
       "sonnet":       {"provider": "claude", "model_id": "claude-sonnet-4-6"},
       "opus":         {"provider": "claude", "model_id": "claude-opus-4-6"},
       "gpt-4o-mini":  {"provider": "openai", "model_id": "gpt-4o-mini"},
       "gpt-4o":       {"provider": "openai", "model_id": "gpt-4o"},
   }
   ```

3. **Per-agent model config** — add to `Settings` table or `.env`:
   ```
   DISCOVERY_AGENT_MODEL=gemini-flash
   SCORING_AGENT_MODEL=gemini-flash
   PARSING_AGENT_MODEL=gemini-flash
   TAILORING_AGENT_MODEL=sonnet
   ```

4. **Update `agents.py`** — constructor accepts `provider: LLMProvider` instead of using a shared client:
   ```python
   class ResumeTailorAgent:
       def __init__(self, provider: LLMProvider):
           self.provider = provider
   ```

5. **Update `server.py` startup** — instantiate providers based on available env vars, pass to agents.

6. **Add model selection to Settings UI** — new `GET/PUT /settings/models` endpoint + frontend section in settings.

7. **Fallback logic** — if primary provider fails, try secondary (similar to harness's `detect_provider_kind()` fallback chain).

### Files to Modify
- `backend/services/resume-tailor/core/llm_client.py` (refactor into providers)
- `backend/services/resume-tailor/core/` (new `llm_providers.py`)
- `backend/services/resume-tailor/core/agents.py` (constructor change)
- `backend/services/resume-tailor/server.py` (startup + new settings routes)
- `backend/services/resume-tailor/database.py` (new settings keys)
- `frontend/app/suggestions/page.tsx` or new settings page

### Expected Impact
- Resolves TODO #1: "assign different agents to different models"
- Scoring agents use cheap/fast models ($0.001/job), tailoring uses best quality (worth the cost)
- Platform resilience: Gemini outage no longer = total downtime
- Cost optimization: with Haiku for scoring, cost per full scan drops ~80%

---

## Feature 4: Token Usage Tracking and Cost Dashboard

**Priority: 4 | Impact: Medium | Effort: Small**

### Problem (Current State)

There is no tracking of how many LLM tokens are consumed per job or per scan. Users have no visibility into API costs. Each Gemini call returns usage metadata that is silently discarded. With 100 jobs scored per scan, API costs can add up unexpectedly.

### Harness Concept Applied

The harness tracks `TokenUsage` per message and cumulates via `UsageTracker` (`usage.rs` §10). `pricing_for_model()` maps model names to per-million-token costs. `format_usd()` renders `$X.XXXX`. `UsageTracker::from_session()` reconstructs cumulative usage from saved session messages.

### What to Build

Track tokens per agent call, store on the `Job` record, and surface totals in the dashboard.

### Actionable Items

1. **Add token tracking to `llm_client.py`** — capture `response.usage_metadata` from Gemini (it's already in the response object, just not used):
   ```python
   @dataclass
   class TokenUsage:
       input_tokens: int = 0
       output_tokens: int = 0
   
   # Return alongside content:
   def generate_content(self, prompt, ...) -> tuple[str, TokenUsage]:
       ...
       usage = TokenUsage(
           input_tokens=response.usage_metadata.prompt_token_count,
           output_tokens=response.usage_metadata.candidates_token_count
       )
       return content, usage
   ```

2. **Add migration** — `004_add_token_usage_to_job.py`:
   ```python
   op.add_column('job', sa.Column('input_tokens', sa.Integer(), nullable=True))
   op.add_column('job', sa.Column('output_tokens', sa.Integer(), nullable=True))
   op.add_column('job', sa.Column('estimated_cost_usd', sa.Float(), nullable=True))
   ```

3. **Update `Job` model** in `database.py`.

4. **Accumulate usage in `process_application()`** across all 3 agent calls, save total to `Job`.

5. **Add pricing lookup** (same pattern as harness):
   ```python
   MODEL_PRICING = {
       "gemini-flash": {"input": 0.075, "output": 0.30},    # per million tokens
       "sonnet":       {"input": 15.0,  "output": 75.0},
       "haiku":        {"input": 1.0,   "output": 5.0},
   }
   ```

6. **Surface in dashboard** — add `estimated_cost` column to the jobs table in `frontend/app/dashboard/page.tsx`.

7. **Add scan-level cost summary** to the scan report modal in `frontend/app/suggestions/page.tsx`.

### Files to Modify
- `backend/services/resume-tailor/core/llm_client.py`
- `backend/services/resume-tailor/database.py`
- `backend/services/resume-tailor/migrations/versions/` (new migration)
- `backend/services/resume-tailor/server.py`
- `frontend/lib/api.ts`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/suggestions/page.tsx`

### Expected Impact
- Surfaces real API spend so users can tune model choices (connects to Feature 3)
- Enables cost-per-application metric ("this resume tailoring cost $0.04")
- Enables per-scan cost visibility ("found 47 jobs, scored 23, cost $0.12 total")
- No architecture change needed — Gemini already returns usage metadata, it's just discarded

---

## Feature 5: Site-Specific Scraper Plugins

**Priority: 5 | Impact: High | Effort: Large**

### Problem (Current State)

The scraper service is a single Playwright-based `POST /scrape` endpoint. Every job site gets the same treatment regardless of its structure. TODO items call out Netflix, Spotify, Microsoft Canada, Uber, and Google as broken. The root cause differs per site:
- LinkedIn requires login
- Google Jobs has dynamic URL rewrites
- Company ATS portals have anti-bot JavaScript
- Some sites need site-specific extraction logic

`resolve_job_url()` in `server.py` (lines 28–53) is a growing pile of per-site hacks that needs to scale.

### Harness Concept Applied

The harness's plugin system (`plugins/src/lib.rs` §8) defines a `PluginManifest` with per-plugin tool commands, lifecycle hooks, and permission requirements. Plugins are loaded from `.claw-plugin/plugin.json` manifests. This is exactly the right model for site-specific scraper logic: each site gets a plugin that knows its structure.

### What to Build

A site plugin system where each job board has a manifest file declaring how to scrape it, how to extract listings, and how to resolve job URLs.

### Actionable Items

1. **Define plugin manifest schema** — create `backend/services/job-scraper/plugins/plugin_schema.py`:
   ```python
   @dataclass
   class SitePluginManifest:
       name: str
       version: str
       domains: list[str]           # e.g. ["linkedin.com", "www.linkedin.com"]
       requires_login: bool         # if True, use saved cookies
       url_pattern: str             # regex to detect if a URL belongs to this site
       listing_extractor: str       # path to Python extractor module
       job_url_resolver: str        # path to URL resolver function
       pagination_strategy: str     # "scroll" | "next_page" | "load_more" | "none"
       wait_selector: str           # CSS selector to wait for before scraping
   ```

2. **Create plugin directory** — `backend/services/job-scraper/plugins/`:
   ```
   plugins/
     google_jobs/
       manifest.json
       extractor.py     # extract_listings(html) -> list[{title, company, url}]
       resolver.py      # resolve_url(relative_url, source_url) -> absolute_url
     linkedin/
       manifest.json
       extractor.py
       resolver.py
     greenhouse/        # generic ATS
       manifest.json
       extractor.py
     lever/
       ...
   ```

3. **Update `job-scraper/main.py`** — on startup, load all plugin manifests; on `/scrape`, select plugin by URL domain match before running Playwright.

4. **Update `server.py` `resolve_job_url()`** (lines 28–53) — delegate to the site plugin's `resolver.py` instead of growing the per-site if/elif chain.

5. **Migrate existing hacks** — move the LinkedIn, Greenhouse, and Lever URL patterns currently in `resolve_job_url()` into their respective plugin `resolver.py` files.

6. **Start with 3 highest-impact plugins:**
   - `google_jobs` — fixes the Google link resolution TODO
   - `linkedin` — largest job board
   - `greenhouse` — most common company ATS

7. **Add plugin health status** to `GET /suggestions/status` response — surface which sites had scraper errors.

### Files to Modify
- `backend/services/job-scraper/main.py` (major refactor)
- `backend/services/job-scraper/plugins/` (new directory)
- `backend/services/resume-tailor/server.py` (lines 28–53, `resolve_job_url`)
- `frontend/app/suggestions/page.tsx` (surface plugin errors)

### Expected Impact
- Fixes TODOs: Netflix, Spotify, Microsoft Canada, Uber, Google (items 3, 5, 7)
- Makes adding support for a new job site a self-contained task (add a plugin, no core changes)
- Fixes URL resolution failures that currently make ~30% of discovered jobs unscrapeable
- Makes scraper extensible without touching the core service

---

## Feature 6: Structured System Prompt Builder for Agents

**Priority: 6 | Impact: Medium | Effort: Small**

### Problem (Current State)

All 4 agents in `agents.py` construct their prompts as multi-line f-strings directly in the method body. The ResumeTailorAgent prompt is 30+ lines of inline string (lines 164–194). Adding context (user preferences, job sector, resume structure) means editing the prompt string directly. There is no reuse between agents for common context like the current date or user's target role.

### Harness Concept Applied

The harness uses `SystemPromptBuilder` (`prompt.rs` §14) to assemble prompts in sections. The boundary marker `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` separates static from dynamic content. `ProjectContext` carries structured data (cwd, date, git status, instruction files) that gets rendered into the prompt. Instruction files (`CLAW.md`) are auto-discovered and injected.

### What to Build

A `AgentPromptBuilder` class that constructs agent prompts in named sections. A user-editable "agent instructions" file (like `CLAW.md`) that gets injected into agent prompts automatically.

### Actionable Items

1. **Create `backend/services/resume-tailor/core/prompt_builder.py`**:
   ```python
   class AgentPromptBuilder:
       def __init__(self):
           self._sections: list[tuple[str, str]] = []
           self._context: dict = {}
   
       def add_section(self, name: str, content: str) -> "AgentPromptBuilder":
           self._sections.append((name, content))
           return self
   
       def with_context(self, **kwargs) -> "AgentPromptBuilder":
           self._context.update(kwargs)
           return self
   
       def with_user_instructions(self, path: str = "./data/instructions.md") -> "AgentPromptBuilder":
           if os.path.exists(path):
               content = open(path).read()[:4000]  # match harness MAX_INSTRUCTION_FILE_CHARS
               self.add_section("User Instructions", content)
           return self
   
       def build(self) -> str:
           rendered = []
           for name, content in self._sections:
               rendered.append(f"## {name}\n{content}")
           if self._context:
               rendered.append(f"## Context\n{json.dumps(self._context, indent=2)}")
           return "\n\n".join(rendered)
   ```

2. **Create `backend/services/resume-tailor/data/instructions.md`** — editable by the user to inject personal context into every agent call:
   ```markdown
   # Personal Career Instructions
   
   Target roles: Senior Software Engineer, Staff Engineer
   Preferred industries: FinTech, DevTools, Infrastructure
   Location preference: Remote or Toronto
   Do not apply to: companies with <50 employees, non-technical managers
   Emphasize: distributed systems experience, Python expertise
   ```

3. **Refactor agent prompts** in `agents.py` to use `AgentPromptBuilder`:
   ```python
   prompt = (AgentPromptBuilder()
       .add_section("Task", "Tailor the following LaTeX resume for this job...")
       .add_section("Job Requirements", job_posting.raw_text)
       .add_section("Master Resume", master_resume)
       .with_user_instructions()
       .with_context(date=datetime.now().isoformat(), job_title=job_posting.job_title)
       .build())
   ```

4. **Add `PUT /settings/instructions` endpoint** in `server.py` — write user's instruction text to `data/instructions.md`.

5. **Add Instructions editor** in the frontend settings section — textarea that saves to the new endpoint.

6. **Add per-job-sector instruction sections** — detect industry from job title and inject sector-specific tips (e.g., finance: emphasize regulatory compliance, startup: emphasize breadth).

### Files to Modify
- `backend/services/resume-tailor/core/agents.py`
- `backend/services/resume-tailor/core/` (new `prompt_builder.py`)
- `backend/services/resume-tailor/data/` (new `instructions.md`)
- `backend/services/resume-tailor/server.py` (new settings route)
- `frontend/app/suggestions/page.tsx` or new settings page

### Expected Impact
- Addresses TODO #9: "resume tailor logic make it based on json experience based structure" — `instructions.md` is the entry point
- Makes agent prompts maintainable without touching Python source
- Enables personalization without code changes (edit instructions.md)
- Directly improves resume tailoring quality by injecting user-specific context

---

## Feature 7: Conversation/Audit Logging per Job Application

**Priority: 7 | Impact: Medium | Effort: Small**

### Problem (Current State)

When `status="failed"` is set, only `str(exception)` is saved to `Job.error_message`. When the resume tailoring produces a poor result, there is no way to see what the LLM was sent or what it replied. There is no way to debug why a particular tailored resume is bad without re-running the pipeline.

### Harness Concept Applied

The harness persists full `Session` objects (conversation history) to JSON files (`session.rs` §3). Each `ConversationMessage` stores the exact content blocks sent and received, including `TokenUsage` per message. Sessions can be loaded, inspected, and replayed.

### What to Build

Save a structured audit log for every job application pipeline run — exact prompts sent, exact responses received, token counts, step timing.

### Actionable Items

1. **Add `audit_log` column** to `Job` in `database.py`:
   ```python
   audit_log: Optional[str] = None  # JSON: list of pipeline step records
   ```
   And migration `004_add_audit_log.py`.

2. **Create `AuditEntry` dataclass** in `core/models.py`:
   ```python
   @dataclass
   class AuditEntry:
       step: str          # "scraping", "parsing", "tailoring", "compiling"
       timestamp: str
       input_preview: str # first 200 chars of input
       output_preview: str # first 200 chars of output
       input_tokens: int
       output_tokens: int
       duration_ms: int
       error: Optional[str] = None
   ```

3. **Collect entries in `process_application()`** (`server.py` lines 255–320) — wrap each agent call with timing and capture.

4. **Save to `Job.audit_log`** as JSON array at pipeline end (regardless of success/failure).

5. **Add `GET /jobs/{job_id}/audit`** endpoint — return parsed audit log.

6. **Add audit view to `jobs/[id]/page.tsx`** — expandable "Pipeline Log" section showing each step, timing, and any errors. On failure, show the full error with context.

### Files to Modify
- `backend/services/resume-tailor/database.py`
- `backend/services/resume-tailor/migrations/versions/` (new file)
- `backend/services/resume-tailor/server.py` (lines 255–320)
- `backend/services/resume-tailor/core/models.py`
- `frontend/app/jobs/[id]/page.tsx`
- `frontend/lib/api.ts`

### Expected Impact
- Changes debugging from "why is status=failed?" to "here's exactly what broke and where"
- Enables quality review: inspect the tailored LaTeX before compiling
- Reduces failed jobs by catching LLM issues early (audit log feeds back into hooks in Feature 2)
- Small database cost: audit log per job is ~2–5KB JSON

---

## Feature 8: Dry-Run / Safe-Scan Permission Mode

**Priority: 8 | Impact: Medium | Effort: Small**

### Problem (Current State)

`POST /apply` immediately starts the full pipeline including expensive LLM calls and PDF compilation. There is no way to test the discovery/scoring flow without committing API spend. There is no way for a user to review what would happen before it does.

### Harness Concept Applied

The harness has `PermissionMode::ReadOnly` which allows read operations but blocks writes (`permissions.rs` §7). The `authorize()` function returns `PermissionOutcome::Deny` with a reason when the active mode is insufficient. This is the "dry run" equivalent.

### What to Build

A `dry_run` query parameter on key endpoints that runs the logic but does not persist results, trigger LLM calls, or compile PDFs.

### Actionable Items

1. **Add `dry_run: bool = False` parameter** to:
   - `POST /apply?dry_run=true` — fetch and parse the job but skip tailoring and PDF; return what it found
   - `POST /suggestions/refresh?dry_run=true` — scrape sources and return discovered jobs without scoring or saving

2. **Implement dry-run logic** in `server.py`:
   ```python
   @app.post("/apply")
   async def apply(request: ApplyRequest, dry_run: bool = False):
       if dry_run:
           # Only scrape + parse, return preview, no DB write
           raw = await scrape_url(request.url)
           parsed = await asyncio.to_thread(parsing_agent.parse, raw["text"])
           return {"preview": True, "company": parsed.company_name, "title": parsed.job_title, ...}
       # ... existing logic
   ```

3. **Add a "Preview" button** to `frontend/app/apply/page.tsx` — calls `POST /apply?dry_run=true` and shows what company/title was detected before the user commits to full tailoring.

4. **Add `scan_preview` mode** to suggestions — show discovered jobs without scoring, let the user select which ones to score/apply.

5. **Store dry_run preference** in `Settings` table — allow users to default all applications to dry-run.

### Files to Modify
- `backend/services/resume-tailor/server.py` (lines 652–679, 806–840)
- `frontend/app/apply/page.tsx`
- `frontend/app/suggestions/page.tsx`
- `frontend/lib/api.ts`

### Expected Impact
- Reduces wasted API spend on bad URLs or pages the scraper can't handle
- Lets users confirm job detection is working before burning Gemini credits
- Provides safety net for new source configurations

---

## Feature 9: Bootstrap Sequence and Startup Health Checks

**Priority: 9 | Impact: Medium | Effort: Small**

### Problem (Current State)

`server.py` startup creates database tables and runs migrations silently. If the Gemini API key is missing, the server starts fine but all agent calls fail with `401 Unauthorized`. If `pdflatex` is not installed, the server starts but PDF compilation fails at runtime. Users have no visibility into what's ready.

### Harness Concept Applied

The harness runs ordered `BootstrapPhase` steps on startup (`bootstrap.rs` §1). Each phase has a specific role. FastPath phases exit early if their condition isn't met. This gives deterministic, observable startup behavior.

### What to Build

Add explicit startup health checks with named phases that surface failures immediately at startup rather than at runtime.

### Actionable Items

1. **Create `backend/services/resume-tailor/core/startup.py`** with ordered phases:
   ```python
   async def run_startup_checks():
       phases = [
           ("database_connection",    check_db_connection),
           ("migrations_applied",     check_migrations_current),
           ("master_resume_exists",   check_master_resume),
           ("gemini_api_key",         check_gemini_key),
           ("scraper_reachable",      check_scraper_service),
           ("pdflatex_available",     check_pdflatex),
       ]
       results = {}
       for name, check in phases:
           try:
               await check()
               results[name] = "ok"
               logger.info(f"Startup: {name} ✓")
           except Exception as e:
               results[name] = f"FAIL: {e}"
               logger.error(f"Startup: {name} FAILED: {e}")
       return results
   ```

2. **Add `GET /health`** endpoint in `server.py` — returns startup check results. Frontend can call this on load.

3. **Call startup checks** in `app` `lifespan` event or at first request.

4. **Surface on frontend** — if `GET /health` returns any failures, show a warning banner in the header with which services are unavailable and what's affected.

5. **Fast-fail on critical missing config** — if `GOOGLE_API_KEY` is absent, log clearly and disable agent endpoints with a `503 Service Unavailable` with a descriptive body.

### Files to Modify
- `backend/services/resume-tailor/server.py`
- `backend/services/resume-tailor/core/` (new `startup.py`)
- `frontend/app/layout.tsx`
- `frontend/lib/api.ts` (add `getHealth()`)

### Expected Impact
- Eliminates "why is everything broken?" debugging on fresh install
- Surfaces `pdflatex` missing immediately instead of on first apply (the #2 reported setup issue)
- Gives operators a `/health` endpoint for container health probes

---

## Feature 10: Session Compaction for Long Job Descriptions

**Priority: 10 | Impact: Low-Medium | Effort: Small**

### Problem (Current State)

The `JobDiscoveryAgent` truncates HTML to `html_content[:40000]` (a fixed char slice). Some job boards have 100KB+ pages. The truncation is silent and can cut off the last 20% of job listings. The `ResumeTailorAgent` passes the full master resume + full job description to Gemini in one shot — if either is very long, the combined prompt exceeds the model's effective context window for quality output.

### Harness Concept Applied

The harness's `compact_session()` algorithm (`compact.rs` §9) uses a token estimation heuristic (`text.len() / 4 + 1`), preserves the most recent messages, and replaces older content with a structured summary. It tracks key files, tools mentioned, and pending work — rather than just truncating blindly.

### What to Build

Replace blind character-slice truncation with a content-aware summarization strategy.

### Actionable Items

1. **Create `content_compactor.py`** in `core/`:
   ```python
   def estimate_tokens(text: str) -> int:
       return len(text) // 4 + 1
   
   def compact_html_for_discovery(html: str, max_tokens: int = 8000) -> str:
       """Extract only text content + links from HTML, then truncate intelligently."""
       # 1. Strip all style/script tags
       # 2. Extract all <a href> links with their text
       # 3. Extract visible text blocks
       # 4. If still > max_tokens, keep first and last 40% (likely where listings are)
       ...
   
   def compact_jd_for_tailoring(jd_text: str, max_tokens: int = 4000) -> str:
       """Keep requirements section + first/last paragraphs, drop boilerplate."""
       # 1. Detect and prioritize "Requirements", "Responsibilities" sections
       # 2. Drop "About Us", "Benefits", "EEO" boilerplate (common patterns)
       # 3. Keep first 100 tokens (job title context) + requirements sections
       ...
   ```

2. **Replace truncation in `agents.py`** (line 28) — use `compact_html_for_discovery()` instead of `html_content[:40000]`.

3. **Apply `compact_jd_for_tailoring()`** before passing to `ResumeTailorAgent` — reduces tailoring prompt length by ~40% on verbose JDs.

4. **Log compaction ratio** — add to audit log (Feature 7) so users can see if JDs are being significantly shortened.

5. **Add `max_jd_tokens` to Settings** — user-configurable limit.

### Files to Modify
- `backend/services/resume-tailor/core/agents.py` (line 28 truncation)
- `backend/services/resume-tailor/core/` (new `content_compactor.py`)
- `backend/services/resume-tailor/server.py`

### Expected Impact
- Fixes partial scrape issues where the last 20% of job listings are cut off
- Reduces prompt token usage by ~30–40% on verbose job descriptions (cost saving)
- Improves tailoring quality by keeping the high-signal parts of the JD

---

## Feature 11: Timezone-Aware Date Handling

**Priority: 11 | Impact: Low | Effort: Small**

### Problem (Current State)

TODO item: "timezone issue pass 7:31 pm counted as the next day?" The `isToday()` function in `dashboard/page.tsx` (line 44–48) compares dates in local browser timezone, but `Job.created_at` is stored as UTC by PostgreSQL. A job created at 11:31 PM UTC appears as "Tomorrow" for a user in UTC-4 (7:31 PM local), splitting their "Today" view incorrectly.

### Harness Concept Applied

The harness injects `current_date` as a string (not a raw timestamp) into `ProjectContext` and uses it explicitly in the system prompt (`prompt.rs` §14). The prompt section reads `"Date: {date}"` — the date is always resolved server-side relative to the server's clock.

### What to Build

Send timezone-aware dates from the backend and fix the frontend comparison.

### Actionable Items

1. **Add timezone to `GET /jobs` response** — return `created_at` as ISO 8601 with timezone offset: `2025-04-02T19:31:00-04:00`

2. **Fix `isToday()` in `dashboard/page.tsx`** — compare dates in UTC by normalizing both sides:
   ```typescript
   function isToday(dateStr: string): boolean {
     const date = new Date(dateStr);
     const now = new Date();
     return date.getUTCFullYear() === now.getUTCFullYear() &&
            date.getUTCMonth() === now.getUTCMonth() &&
            date.getUTCDate() === now.getUTCDate();
   }
   ```
   Or, send a `today_date` field from the server in `GET /jobs` response and compare against that.

3. **Add `GET /settings/server-time`** endpoint — returns the server's current time as ISO 8601. Frontend uses this as the reference for "today" grouping.

4. **Standardize all timestamp displays** — use `Intl.DateTimeFormat` with `timeZoneName: "short"` so the user knows what timezone is shown.

### Files to Modify
- `frontend/app/dashboard/page.tsx` (lines 44–48)
- `backend/services/resume-tailor/server.py` (timestamp serialization)
- `frontend/lib/api.ts`

### Expected Impact
- Fixes TODO #8 (timezone issue)
- Small change, high correctness improvement — stops jobs appearing in the wrong day group

---

## Summary Table

| # | Feature | Priority | Impact | Effort | Key Files |
|---|---------|----------|--------|--------|-----------|
| 1 | Real-time SSE Progress | 1 | High | Medium | `server.py`, `jobs/[id]/page.tsx` |
| 2 | Pre/Post Agent Hooks | 2 | High | Medium | `agents.py`, new `hooks.py` |
| 3 | Multi-Provider LLM | 3 | High | Medium | `llm_client.py`, `agents.py` |
| 4 | Token Cost Tracking | 4 | Medium | Small | `llm_client.py`, `database.py` |
| 5 | Site Scraper Plugins | 5 | High | Large | `job-scraper/main.py` |
| 6 | Prompt Builder + User Instructions | 6 | Medium | Small | `agents.py`, new `prompt_builder.py` |
| 7 | Audit Log per Application | 7 | Medium | Small | `database.py`, `server.py` |
| 8 | Dry-Run Mode | 8 | Medium | Small | `server.py`, `apply/page.tsx` |
| 9 | Startup Health Checks | 9 | Medium | Small | new `startup.py`, `server.py` |
| 10 | Content-Aware Compaction | 10 | Low-Med | Small | `agents.py`, new `content_compactor.py` |
| 11 | Timezone Fix | 11 | Low | Small | `dashboard/page.tsx` |

---

## Recommended Build Order

**Phase 1 (Reliability):** Features 9 → 11 → 2
Start with startup health checks and the timezone fix (both are small and unblock trust in the system), then add hooks to catch LaTeX failures.

**Phase 2 (Observability):** Features 4 → 7 → 1
Track costs and add audit logging before building the streaming UI — you need the per-step data to power the stream events.

**Phase 3 (Quality):** Features 6 → 10 → 3
Improve prompt quality and content compaction before adding new LLM providers — better prompts compound across all models.

**Phase 4 (Extensibility):** Features 8 → 5
Add dry-run for safe testing, then build the plugin system for new job sites.

---

## Cross-Cutting Concern: Thread Safety on `scan_status`

Not a feature but a required fix before building Features 1 or 8:

The global `scan_status` dict in `server.py` (lines 79–92) is mutated by background tasks and read by the status polling endpoint without any locking. With concurrent scans or multiple simultaneous requests, this can produce corrupted scan status reads. Replace with a per-scan `asyncio.Queue` (the same mechanism as Feature 1's event bus) or an `asyncio.Lock`-protected dict.
