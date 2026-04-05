# Event-Driven Pipeline Architecture Design

**Date:** 2026-04-04  
**Features:** Real-Time Streaming Progress (SSE), Pre/Post Agent Hooks, Bootstrap Health Checks  
**Approach:** Event-Driven Architecture with Centralized Event Bus

---

## 1. Problem Statement

AutoCareer currently has three critical gaps in reliability and user experience:

1. **No Real-Time Progress Visibility** - Users see static "Processing..." during 10-30 second resume tailoring operations with no indication of progress, stalls, or failures
2. **No Quality Control for AI Agents** - The 4 AI agents execute with no validation layer; when LLMs output broken LaTeX, jobs fail with cryptic error messages
3. **No Startup Health Verification** - Critical configuration errors (missing API keys, missing pdflatex) only surface at runtime, not on server startup

These issues share a common architectural need: **structured event emission and handling across the pipeline**.

---

## 2. Goals and Non-Goals

### Goals

- **G1:** Provide real-time, sub-second progress updates during resume tailoring pipeline
- **G2:** Enable pre/post validation hooks for all AI agent calls with fail-fast behavior
- **G3:** Verify all critical dependencies on server startup and block startup if misconfigured
- **G4:** Support automatic retry (up to 3 attempts) and manual retry for failed jobs
- **G5:** Create an extensible event system that future features (audit logging, cost tracking) can leverage
- **G6:** Keep events in-memory for real-time streaming (no database writes for event storage)

### Non-Goals

- **NG1:** Persistent event storage (audit logging is Feature 7, comes later)
- **NG2:** Multi-server event synchronization (single-server deployment only)
- **NG3:** Historical event replay (events only available during active processing)
- **NG4:** Custom user-defined hooks via UI (environment variable configuration only)

---

## 3. Architecture Overview

### Event-Driven System Components

```
┌─────────────────────────────────────────────────────────────┐
│                     Event Bus (EventBus)                    │
│  - Per-job asyncio.Queue for event routing                 │
│  - Global startup event queue for health checks             │
│  - Event emission APIs for pipeline stages                 │
└─────────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
          ▼               ▼               ▼
    ┌──────────┐    ┌──────────┐    ┌──────────┐
    │ SSE      │    │ Agent    │    │ Health   │
    │ Streaming│    │ Hooks    │    │ Checks   │
    └──────────┘    └──────────┘    └──────────┘
          │               │               │
          │               │               │
          ▼               ▼               ▼
    Frontend        process_application    Server
    EventSource     Pipeline Stages        Startup
```

### Event Flow Example (Resume Tailoring)

```
User clicks "Apply"
  → POST /apply creates job with status="processing"
  → Background task starts process_application(job_id)
  → EventBus creates Queue for job_id

1. Pre-hook: validate_master_resume_exists
   → emits: {"type": "hook_validated", "hook": "pre_scrape"}
   
2. Scrape job URL
   → emits: {"type": "step_started", "step": "scraping"}
   → scrapes HTML
   → emits: {"type": "step_completed", "step": "scraping"}

3. Pre-hook: validate_html_content
   → emits: {"type": "hook_validated", "hook": "pre_parse"}
   
4. Parse job description (JobParsingAgent)
   → emits: {"type": "step_started", "step": "parsing"}
   → AI extracts company, title, requirements
   → emits: {"type": "step_completed", "step": "parsing", "data": {...}}
   
5. Post-hook: validate_parsing_completeness
   → emits: {"type": "hook_validated", "hook": "post_parse"}

6. Tailor resume (ResumeTailorAgent)
   → emits: {"type": "step_started", "step": "tailoring"}
   → AI rewrites LaTeX
   → emits: {"type": "step_completed", "step": "tailoring"}
   
7. Post-hook: validate_latex_syntax
   → Validates LaTeX structure
   → IF INVALID:
       → emits: {"type": "hook_failed", "hook": "post_tailor", "error": "..."}
       → emits: {"type": "retry_attempt", "attempt": 1, "max": 3}
       → RETRY from step 6
   → IF VALID:
       → emits: {"type": "hook_validated", "hook": "post_tailor"}

8. Compile PDF
   → emits: {"type": "step_started", "step": "compiling"}
   → Runs pdflatex
   → emits: {"type": "step_completed", "step": "compiling", "pdf_path": "..."}

9. Save to database
   → emits: {"type": "pipeline_completed", "job_id": X, "status": "applied"}

Frontend receives all events via SSE and displays progress in real-time.
```

---

## 4. Component Design

### 4.1 Event Bus (`core/event_bus.py`)

**Purpose:** Central event routing system with per-job queues.

**Data Structures:**

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, List
from datetime import datetime
from enum import Enum
import asyncio

class EventType(str, Enum):
    # Pipeline lifecycle
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"
    
    # Step events
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    
    # Hook events
    HOOK_STARTED = "hook_started"
    HOOK_VALIDATED = "hook_validated"
    HOOK_FAILED = "hook_failed"
    HOOK_WARNED = "hook_warned"
    
    # Retry events
    RETRY_ATTEMPT = "retry_attempt"
    RETRY_EXHAUSTED = "retry_exhausted"
    
    # Health check events
    HEALTH_CHECK_STARTED = "health_check_started"
    HEALTH_CHECK_PASSED = "health_check_passed"
    HEALTH_CHECK_FAILED = "health_check_failed"

@dataclass
class JobEvent:
    """Represents a single event in the job processing pipeline."""
    type: EventType
    timestamp: datetime
    job_id: Optional[int] = None
    step: Optional[str] = None  # scraping, parsing, tailoring, compiling
    hook: Optional[str] = None  # Hook name
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict for SSE."""
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "job_id": self.job_id,
            "step": self.step,
            "hook": self.hook,
            "data": self.data,
            "error": self.error,
        }

class EventBus:
    """Central event routing system with per-job queues."""
    
    def __init__(self):
        self._job_queues: Dict[int, asyncio.Queue] = {}
        self._startup_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
    
    async def create_job_queue(self, job_id: int) -> asyncio.Queue:
        """Create a queue for a specific job."""
        async with self._lock:
            if job_id in self._job_queues:
                return self._job_queues[job_id]
            queue = asyncio.Queue()
            self._job_queues[job_id] = queue
            return queue
    
    async def emit(self, event: JobEvent):
        """Emit an event to the appropriate queue."""
        if event.job_id is not None:
            async with self._lock:
                if event.job_id in self._job_queues:
                    await self._job_queues[event.job_id].put(event)
        else:
            # Startup/health events
            await self._startup_queue.put(event)
    
    async def get_job_queue(self, job_id: int) -> Optional[asyncio.Queue]:
        """Get the queue for a specific job."""
        async with self._lock:
            return self._job_queues.get(job_id)
    
    async def cleanup_job_queue(self, job_id: int):
        """Remove a job's queue after processing completes."""
        async with self._lock:
            if job_id in self._job_queues:
                del self._job_queues[job_id]
    
    def get_startup_queue(self) -> asyncio.Queue:
        """Get the startup/health check event queue."""
        return self._startup_queue

# Global singleton instance
event_bus = EventBus()
```

**API:**

- `create_job_queue(job_id)` - Initialize queue for new job
- `emit(event)` - Publish event to appropriate queue
- `get_job_queue(job_id)` - Retrieve queue for SSE streaming
- `cleanup_job_queue(job_id)` - Remove queue after completion
- `get_startup_queue()` - Get health check event queue

---

### 4.2 Agent Hook System (`core/hooks.py`)

**Purpose:** Validation layer that wraps AI agent calls with pre/post checks.

**Hook Interface:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

class HookResult(str, Enum):
    ALLOW = "allow"      # Validation passed, continue
    DENY = "deny"        # Validation failed, abort pipeline
    WARN = "warn"        # Validation concern, log but continue

@dataclass
class HookContext:
    """Context passed to hook functions."""
    agent_name: str
    job_id: int
    input_data: Any
    output_data: Optional[Any] = None

class Hook(ABC):
    """Base class for all hooks."""
    
    @abstractmethod
    def name(self) -> str:
        """Hook identifier."""
        pass
    
    @abstractmethod
    def execute(self, context: HookContext) -> tuple[HookResult, Optional[str]]:
        """
        Execute the hook validation.
        
        Returns:
            (HookResult, error_message)
        """
        pass

class ValidateMasterResumeExists(Hook):
    """Pre-hook: Ensure master resume file exists and is valid LaTeX."""
    
    def name(self) -> str:
        return "validate_master_resume_exists"
    
    def execute(self, context: HookContext) -> tuple[HookResult, Optional[str]]:
        master_resume_path = context.input_data.get("master_resume_path")
        if not master_resume_path or not Path(master_resume_path).exists():
            return HookResult.DENY, f"Master resume not found: {master_resume_path}"
        
        # Basic LaTeX validation
        with open(master_resume_path, 'r') as f:
            content = f.read()
            if "\\documentclass" not in content:
                return HookResult.DENY, "Master resume missing \\documentclass"
            if "\\begin{document}" not in content:
                return HookResult.DENY, "Master resume missing \\begin{document}"
        
        return HookResult.ALLOW, None

class ValidateTailoredLatex(Hook):
    """Post-hook: Validate LaTeX output from ResumeTailorAgent."""
    
    def name(self) -> str:
        return "validate_tailored_latex"
    
    def execute(self, context: HookContext) -> tuple[HookResult, Optional[str]]:
        latex = context.output_data
        
        # Check for common LLM mistakes
        errors = []
        
        # 1. Unclosed braces
        if latex.count("{") != latex.count("}"):
            errors.append("Unbalanced braces")
        
        # 2. Markdown artifacts
        if "```" in latex or "```latex" in latex:
            errors.append("Contains markdown code fence artifacts")
        
        # 3. Required LaTeX structure
        if "\\documentclass" not in latex:
            errors.append("Missing \\documentclass")
        if "\\begin{document}" not in latex:
            errors.append("Missing \\begin{document}")
        if "\\end{document}" not in latex:
            errors.append("Missing \\end{document}")
        
        # 4. Common broken commands
        broken_patterns = [r"\\item\s*\n\s*\\item", r"\\end{[^}]+}\s*\n\s*[^\\]"]
        for pattern in broken_patterns:
            import re
            if re.search(pattern, latex):
                errors.append(f"Potential LaTeX structure issue: {pattern}")
        
        if errors:
            return HookResult.DENY, "; ".join(errors)
        
        return HookResult.ALLOW, None

class WarnOnLowScore(Hook):
    """Post-hook: Warn if job score is below threshold."""
    
    def name(self) -> str:
        return "warn_on_low_score"
    
    def execute(self, context: HookContext) -> tuple[HookResult, Optional[str]]:
        score = context.output_data.get("score")
        if score is not None and score < 30:
            return HookResult.WARN, f"Low match score: {score}/100"
        return HookResult.ALLOW, None

class LogAgentOutput(Hook):
    """Post-hook: Structured logging for all agent outputs."""
    
    def name(self) -> str:
        return "log_agent_output"
    
    def execute(self, context: HookContext) -> tuple[HookResult, Optional[str]]:
        import logging
        logger = logging.getLogger(f"agent.{context.agent_name}")
        
        output_preview = str(context.output_data)[:200] if context.output_data else "None"
        logger.info(
            f"Agent={context.agent_name} JobID={context.job_id} "
            f"Output={output_preview}..."
        )
        
        return HookResult.ALLOW, None
```

**Hook Runner:**

```python
from typing import List, Optional
from core.event_bus import event_bus, JobEvent, EventType
from datetime import datetime

class AgentHookRunner:
    """Executes hooks around agent calls."""
    
    def __init__(self):
        self._enabled = os.getenv("AGENT_HOOKS_ENABLED", "true").lower() == "true"
        self._hooks = self._load_hooks()
    
    def _load_hooks(self) -> Dict[str, List[Hook]]:
        """Load hook configuration from environment."""
        # Hook configuration format:
        # PRE_TAILOR_HOOKS=validate_master_resume_exists
        # POST_TAILOR_HOOKS=validate_tailored_latex,log_agent_output
        
        hooks = {
            "pre_scrape": [],
            "post_scrape": [],
            "pre_parse": [],
            "post_parse": [],
            "pre_score": [],
            "post_score": [WarnOnLowScore()],
            "pre_tailor": [ValidateMasterResumeExists()],
            "post_tailor": [ValidateTailoredLatex(), LogAgentOutput()],
        }
        
        # Override with env config if present
        for stage in ["scrape", "parse", "score", "tailor"]:
            pre_var = f"PRE_{stage.upper()}_HOOKS"
            post_var = f"POST_{stage.upper()}_HOOKS"
            
            if pre_hooks := os.getenv(pre_var):
                hooks[f"pre_{stage}"] = self._parse_hook_list(pre_hooks)
            if post_hooks := os.getenv(post_var):
                hooks[f"post_{stage}"] = self._parse_hook_list(post_hooks)
        
        return hooks
    
    def _parse_hook_list(self, hook_names: str) -> List[Hook]:
        """Parse comma-separated hook names into Hook instances."""
        hook_map = {
            "validate_master_resume_exists": ValidateMasterResumeExists(),
            "validate_tailored_latex": ValidateTailoredLatex(),
            "warn_on_low_score": WarnOnLowScore(),
            "log_agent_output": LogAgentOutput(),
        }
        return [hook_map[name.strip()] for name in hook_names.split(",") if name.strip() in hook_map]
    
    async def run_pre_hooks(self, stage: str, context: HookContext) -> Optional[str]:
        """
        Run pre-hooks for a stage.
        
        Returns:
            None if all hooks pass, error message if any hook denies
        """
        if not self._enabled:
            return None
        
        hooks = self._hooks.get(f"pre_{stage}", [])
        
        for hook in hooks:
            await event_bus.emit(JobEvent(
                type=EventType.HOOK_STARTED,
                timestamp=datetime.utcnow(),
                job_id=context.job_id,
                hook=hook.name(),
            ))
            
            result, error = await asyncio.to_thread(hook.execute, context)
            
            if result == HookResult.DENY:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_FAILED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                    error=error,
                ))
                return error
            elif result == HookResult.WARN:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_WARNED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                    error=error,
                ))
            else:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_VALIDATED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                ))
        
        return None
    
    async def run_post_hooks(self, stage: str, context: HookContext) -> Optional[str]:
        """Run post-hooks for a stage. Same signature as run_pre_hooks."""
        if not self._enabled:
            return None
        
        hooks = self._hooks.get(f"post_{stage}", [])
        
        for hook in hooks:
            await event_bus.emit(JobEvent(
                type=EventType.HOOK_STARTED,
                timestamp=datetime.utcnow(),
                job_id=context.job_id,
                hook=hook.name(),
            ))
            
            result, error = await asyncio.to_thread(hook.execute, context)
            
            if result == HookResult.DENY:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_FAILED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                    error=error,
                ))
                return error
            elif result == HookResult.WARN:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_WARNED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                    error=error,
                ))
            else:
                await event_bus.emit(JobEvent(
                    type=EventType.HOOK_VALIDATED,
                    timestamp=datetime.utcnow(),
                    job_id=context.job_id,
                    hook=hook.name(),
                ))
        
        return None

# Global singleton
hook_runner = AgentHookRunner()
```

---

### 4.3 Health Check System (`core/startup.py`)

**Purpose:** Verify all critical dependencies before starting the server.

**Health Check Interface:**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import httpx
import subprocess
from pathlib import Path

@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    passed: bool
    error: Optional[str] = None
    details: Optional[dict] = None

class HealthCheck(ABC):
    """Base class for startup health checks."""
    
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def is_critical(self) -> bool:
        """If True, server startup fails if check fails."""
        pass
    
    @abstractmethod
    async def check(self) -> HealthCheckResult:
        pass

class DatabaseConnectionCheck(HealthCheck):
    def name(self) -> str:
        return "database_connection"
    
    def is_critical(self) -> bool:
        return True
    
    async def check(self) -> HealthCheckResult:
        try:
            from database import engine
            from sqlmodel import Session, select, text
            
            with Session(engine) as session:
                session.exec(text("SELECT 1"))
            
            return HealthCheckResult(
                name=self.name(),
                passed=True,
                details={"backend": get_active_backend()}
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error=str(e)
            )

class MigrationStatusCheck(HealthCheck):
    def name(self) -> str:
        return "migrations_applied"
    
    def is_critical(self) -> bool:
        return True
    
    async def check(self) -> HealthCheckResult:
        try:
            # Check if alembic_version table exists
            from database import engine
            from sqlmodel import Session, text
            
            with Session(engine) as session:
                result = session.exec(text(
                    "SELECT version_num FROM alembic_version"
                )).first()
            
            return HealthCheckResult(
                name=self.name(),
                passed=True,
                details={"current_revision": result}
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error="Database not migrated. Run: alembic upgrade head"
            )

class MasterResumeCheck(HealthCheck):
    def name(self) -> str:
        return "master_resume_exists"
    
    def is_critical(self) -> bool:
        return True
    
    async def check(self) -> HealthCheckResult:
        resume_path = os.getenv("MASTER_RESUME_PATH", "./data/master.tex")
        path = Path(resume_path)
        
        if not path.exists():
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error=f"Master resume not found: {resume_path}"
            )
        
        # Validate basic LaTeX structure
        with open(path, 'r') as f:
            content = f.read()
            if "\\documentclass" not in content:
                return HealthCheckResult(
                    name=self.name(),
                    passed=False,
                    error="Master resume missing \\documentclass"
                )
        
        return HealthCheckResult(
            name=self.name(),
            passed=True,
            details={"path": str(path.absolute())}
        )

class GeminiAPIKeyCheck(HealthCheck):
    def name(self) -> str:
        return "gemini_api_key"
    
    def is_critical(self) -> bool:
        return True
    
    async def check(self) -> HealthCheckResult:
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error="GOOGLE_API_KEY environment variable not set"
            )
        
        # Optional: Test API key with a minimal request
        # (skipped to avoid startup delay, key is just checked for presence)
        
        return HealthCheckResult(
            name=self.name(),
            passed=True,
            details={"configured": True}
        )

class ScraperServiceCheck(HealthCheck):
    def name(self) -> str:
        return "scraper_reachable"
    
    def is_critical(self) -> bool:
        return False  # Non-critical: jobs will fail gracefully
    
    async def check(self) -> HealthCheckResult:
        scraper_url = os.getenv("SCRAPER_SERVICE_URL", "http://scraper:8001")
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{scraper_url}/health")
                response.raise_for_status()
            
            return HealthCheckResult(
                name=self.name(),
                passed=True,
                details={"url": scraper_url}
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error=f"Scraper unreachable: {e}"
            )

class PdflatexCheck(HealthCheck):
    def name(self) -> str:
        return "pdflatex_available"
    
    def is_critical(self) -> bool:
        return True
    
    async def check(self) -> HealthCheckResult:
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["pdflatex", "--version"],
                capture_output=True,
                timeout=5
            )
            
            if result.returncode == 0:
                version = result.stdout.decode().split('\n')[0]
                return HealthCheckResult(
                    name=self.name(),
                    passed=True,
                    details={"version": version}
                )
            else:
                return HealthCheckResult(
                    name=self.name(),
                    passed=False,
                    error="pdflatex command failed"
                )
        except FileNotFoundError:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error="pdflatex not found. Install TeX Live."
            )
        except Exception as e:
            return HealthCheckResult(
                name=self.name(),
                passed=False,
                error=str(e)
            )
```

**Health Check Runner:**

```python
class HealthCheckRunner:
    """Runs all health checks on startup."""
    
    def __init__(self):
        self.checks: List[HealthCheck] = [
            DatabaseConnectionCheck(),
            MigrationStatusCheck(),
            MasterResumeCheck(),
            GeminiAPIKeyCheck(),
            ScraperServiceCheck(),
            PdflatexCheck(),
        ]
    
    async def run_all(self) -> dict[str, HealthCheckResult]:
        """Run all health checks and return results."""
        results = {}
        
        for check in self.checks:
            await event_bus.emit(JobEvent(
                type=EventType.HEALTH_CHECK_STARTED,
                timestamp=datetime.utcnow(),
                data={"check": check.name()}
            ))
            
            result = await check.check()
            results[check.name()] = result
            
            if result.passed:
                await event_bus.emit(JobEvent(
                    type=EventType.HEALTH_CHECK_PASSED,
                    timestamp=datetime.utcnow(),
                    data={"check": check.name(), "details": result.details}
                ))
            else:
                await event_bus.emit(JobEvent(
                    type=EventType.HEALTH_CHECK_FAILED,
                    timestamp=datetime.utcnow(),
                    data={"check": check.name()},
                    error=result.error
                ))
        
        return results
    
    def get_critical_failures(self, results: dict[str, HealthCheckResult]) -> List[str]:
        """Get list of critical check failures."""
        failures = []
        for check in self.checks:
            if check.is_critical():
                result = results.get(check.name())
                if result and not result.passed:
                    failures.append(f"{check.name()}: {result.error}")
        return failures

# Global singleton
health_runner = HealthCheckRunner()
```

**Server Integration:**

```python
# In server.py

startup_results = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    global startup_results
    
    # Run database setup
    create_db_and_tables()
    if SYNC_ON_BOOT:
        await _run_db_reconcile("startup")
    
    # Run health checks
    logger.info("Running startup health checks...")
    startup_results = await health_runner.run_all()
    
    # Check for critical failures
    failures = health_runner.get_critical_failures(startup_results)
    if failures:
        logger.error("Critical health checks failed:")
        for failure in failures:
            logger.error(f"  - {failure}")
        raise RuntimeError(
            "Server startup aborted due to critical health check failures. "
            f"Fix these issues: {', '.join(failures)}"
        )
    
    logger.info("All critical health checks passed. Server starting...")
    yield
    
    if SYNC_ON_SHUTDOWN:
        await _run_db_reconcile("shutdown")

@app.get("/health")
async def health_endpoint():
    """Health check endpoint returning startup check results."""
    return {
        "status": "healthy",
        "checks": {
            name: {
                "passed": result.passed,
                "error": result.error,
                "details": result.details
            }
            for name, result in startup_results.items()
        }
    }
```

---

### 4.4 SSE Streaming (`server.py` additions)

**Purpose:** Stream events to frontend in real-time via Server-Sent Events.

**SSE Endpoint:**

```python
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator

async def event_stream(job_id: int) -> AsyncGenerator[str, None]:
    """
    Generate SSE stream for a specific job.
    
    Yields:
        SSE-formatted event strings
    """
    queue = await event_bus.get_job_queue(job_id)
    
    if not queue:
        # Job not found or already completed
        yield f"data: {json.dumps({'type': 'error', 'error': 'Job queue not found'})}\n\n"
        return
    
    try:
        while True:
            try:
                # Wait for next event with timeout
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                
                # Convert to SSE format
                data = json.dumps(event.to_dict())
                yield f"data: {data}\n\n"
                
                # If pipeline completed or failed, close stream
                if event.type in [EventType.PIPELINE_COMPLETED, EventType.PIPELINE_FAILED]:
                    break
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                yield f": keepalive\n\n"
                
    except asyncio.CancelledError:
        logger.info(f"SSE stream cancelled for job {job_id}")
    finally:
        # Client disconnected or pipeline finished
        pass

@app.get("/jobs/{job_id}/stream")
async def stream_job_progress(job_id: int):
    """
    Server-Sent Events endpoint for real-time job progress.
    
    Returns:
        SSE stream of pipeline events
    """
    # Verify job exists
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
    
    return StreamingResponse(
        event_stream(job_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
```

---

### 4.5 Modified Pipeline with Events and Hooks

**Updated `process_application` function:**

```python
from core.event_bus import event_bus, JobEvent, EventType
from core.hooks import hook_runner, HookContext
from datetime import datetime

MAX_RETRIES = 3

async def process_application(job_id: int, url: str):
    """
    Process a job application with event emission and hook validation.
    
    Supports automatic retry on hook failures (up to MAX_RETRIES).
    """
    logger.info(f"Starting processing for job {job_id} with URL: {url}")
    
    # Create event queue for this job
    await event_bus.create_job_queue(job_id)
    
    # Emit pipeline start event
    await event_bus.emit(JobEvent(
        type=EventType.PIPELINE_STARTED,
        timestamp=datetime.utcnow(),
        job_id=job_id,
        data={"url": url}
    ))
    
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            logger.error(f"Job {job_id} not found in database")
            await event_bus.cleanup_job_queue(job_id)
            return

        try:
            # ===== STEP 1: SCRAPE =====
            await event_bus.emit(JobEvent(
                type=EventType.STEP_STARTED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="scraping"
            ))
            
            logger.debug(f"Scraping URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{SCRAPER_SERVICE_URL}/scrape",
                    json={"url": url},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                raw_text = data["text"]
            
            await event_bus.emit(JobEvent(
                type=EventType.STEP_COMPLETED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="scraping",
                data={"text_length": len(raw_text)}
            ))
            logger.debug("Scraping completed successfully")
            
            # ===== STEP 2: PARSE (with hooks) =====
            await event_bus.emit(JobEvent(
                type=EventType.STEP_STARTED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="parsing"
            ))
            
            # Pre-hook
            pre_context = HookContext(
                agent_name="JobParsingAgent",
                job_id=job_id,
                input_data={"raw_text": raw_text[:500]}  # Preview only
            )
            if error := await hook_runner.run_pre_hooks("parse", pre_context):
                raise ValueError(f"Pre-parse hook failed: {error}")
            
            # Run agent
            logger.debug("Parsing job description")
            parsing_agent = JobParsingAgent()
            job_posting = await asyncio.to_thread(parsing_agent.parse, raw_text)
            
            # Post-hook
            post_context = HookContext(
                agent_name="JobParsingAgent",
                job_id=job_id,
                input_data={"raw_text": raw_text[:500]},
                output_data=job_posting.model_dump()
            )
            if error := await hook_runner.run_post_hooks("parse", post_context):
                raise ValueError(f"Post-parse hook failed: {error}")
            
            # Update job details
            job.company = job_posting.company_name
            job.title = job_posting.job_title
            if job_posting.key_requirements:
                job.requirements = json.dumps(job_posting.key_requirements)
            session.add(job)
            session.commit()
            
            await event_bus.emit(JobEvent(
                type=EventType.STEP_COMPLETED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="parsing",
                data={
                    "company": job_posting.company_name,
                    "title": job_posting.job_title,
                    "requirements_count": len(job_posting.key_requirements or [])
                }
            ))
            logger.info(f"Job parsed: {job.company} - {job.title}")
            
            # ===== STEP 3: TAILOR (with hooks and retry) =====
            attempt = 0
            tailored_latex = None
            
            while attempt < MAX_RETRIES:
                attempt += 1
                
                if attempt > 1:
                    await event_bus.emit(JobEvent(
                        type=EventType.RETRY_ATTEMPT,
                        timestamp=datetime.utcnow(),
                        job_id=job_id,
                        step="tailoring",
                        data={"attempt": attempt, "max_retries": MAX_RETRIES}
                    ))
                
                await event_bus.emit(JobEvent(
                    type=EventType.STEP_STARTED,
                    timestamp=datetime.utcnow(),
                    job_id=job_id,
                    step="tailoring",
                    data={"attempt": attempt}
                ))
                
                try:
                    # Pre-hook
                    master_latex = load_master_resume(MASTER_RESUME_PATH)
                    pre_context = HookContext(
                        agent_name="ResumeTailorAgent",
                        job_id=job_id,
                        input_data={
                            "master_resume_path": MASTER_RESUME_PATH,
                            "job_posting": job_posting.model_dump()
                        }
                    )
                    if error := await hook_runner.run_pre_hooks("tailor", pre_context):
                        raise ValueError(f"Pre-tailor hook failed: {error}")
                    
                    # Run agent
                    logger.debug(f"Tailoring resume (attempt {attempt})")
                    tailor_agent = ResumeTailorAgent()
                    tailored_latex = await asyncio.to_thread(
                        tailor_agent.tailor,
                        master_latex,
                        job_posting
                    )
                    
                    # Post-hook (this validates LaTeX)
                    post_context = HookContext(
                        agent_name="ResumeTailorAgent",
                        job_id=job_id,
                        input_data={"master_latex": master_latex[:500]},
                        output_data=tailored_latex
                    )
                    if error := await hook_runner.run_post_hooks("tailor", post_context):
                        if attempt < MAX_RETRIES:
                            logger.warning(
                                f"Post-tailor hook failed (attempt {attempt}): {error}. Retrying..."
                            )
                            continue  # Retry
                        else:
                            raise ValueError(f"Post-tailor hook failed after {MAX_RETRIES} attempts: {error}")
                    
                    # Success!
                    await event_bus.emit(JobEvent(
                        type=EventType.STEP_COMPLETED,
                        timestamp=datetime.utcnow(),
                        job_id=job_id,
                        step="tailoring",
                        data={"latex_length": len(tailored_latex)}
                    ))
                    break  # Exit retry loop
                    
                except Exception as e:
                    if attempt < MAX_RETRIES:
                        logger.warning(f"Tailoring failed (attempt {attempt}): {e}. Retrying...")
                        await asyncio.sleep(1)  # Brief delay before retry
                        continue
                    else:
                        await event_bus.emit(JobEvent(
                            type=EventType.RETRY_EXHAUSTED,
                            timestamp=datetime.utcnow(),
                            job_id=job_id,
                            step="tailoring",
                            error=str(e)
                        ))
                        raise
            
            # ===== STEP 4: COMPILE =====
            await event_bus.emit(JobEvent(
                type=EventType.STEP_STARTED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="compiling"
            ))
            
            logger.debug("Compiling PDF")
            company_name = "".join(c for c in job_posting.company_name if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            job_title = "".join(c for c in job_posting.job_title if c.isalnum() or c in (' ', '-', '_')).strip().replace(' ', '_')
            
            pdf_path = await asyncio.to_thread(
                compile_pdf,
                latex_content=tailored_latex,
                output_dir="./output",
                company_name=company_name,
                job_title=job_title,
                cleanup=True
            )
            
            await event_bus.emit(JobEvent(
                type=EventType.STEP_COMPLETED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                step="compiling",
                data={"pdf_path": pdf_path}
            ))
            
            # ===== STEP 5: SAVE =====
            job.pdf_path = pdf_path
            job.status = "applied"
            session.add(job)
            session.commit()
            
            await event_bus.emit(JobEvent(
                type=EventType.PIPELINE_COMPLETED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                data={"status": "applied", "pdf_path": pdf_path}
            ))
            logger.info(f"Job {job_id} processing completed successfully. PDF saved at {pdf_path}")
            
        except Exception as e:
            logger.exception(f"Error processing job {job_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            session.add(job)
            session.commit()
            
            await event_bus.emit(JobEvent(
                type=EventType.PIPELINE_FAILED,
                timestamp=datetime.utcnow(),
                job_id=job_id,
                error=str(e)
            ))
        
        finally:
            # Cleanup event queue after a delay (allow SSE to drain)
            await asyncio.sleep(5)
            await event_bus.cleanup_job_queue(job_id)
```

---

### 4.6 Frontend Integration

**New SSE Hook (`frontend/lib/useJobStream.ts`):**

```typescript
import { useEffect, useRef, useState } from 'react';

export interface JobStreamEvent {
  type: string;
  timestamp: string;
  job_id?: number;
  step?: string;
  hook?: string;
  data?: any;
  error?: string;
}

export function useJobStream(jobId: number | null) {
  const [events, setEvents] = useState<JobStreamEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!jobId) return;

    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(`${apiUrl}/jobs/${jobId}/stream`);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      setIsConnected(true);
      setError(null);
    };

    eventSource.onmessage = (e) => {
      try {
        const event: JobStreamEvent = JSON.parse(e.data);
        setEvents((prev) => [...prev, event]);

        // Close connection if pipeline completed or failed
        if (event.type === 'pipeline_completed' || event.type === 'pipeline_failed') {
          eventSource.close();
          setIsConnected(false);
        }
      } catch (err) {
        console.error('Failed to parse SSE event:', err);
      }
    };

    eventSource.onerror = () => {
      setError('Connection lost');
      setIsConnected(false);
      eventSource.close();
    };

    return () => {
      eventSource.close();
      setIsConnected(false);
    };
  }, [jobId]);

  return { events, isConnected, error };
}
```

**Updated Job Details Page (`frontend/app/jobs/[id]/page.tsx`):**

```typescript
'use client';

import { useJobStream, JobStreamEvent } from '@/lib/useJobStream';
import { Progress } from '@/components/ui/progress';
import { CheckCircle2, Circle, AlertCircle, Loader2 } from 'lucide-react';

// Inside JobDetailsPage component:

const { events, isConnected } = useJobStream(job.status === 'processing' ? id : null);

// Progress calculation
const steps = ['scraping', 'parsing', 'tailoring', 'compiling'];
const currentStepIndex = events.reduce((max, event) => {
  if (event.type === 'step_started' && event.step) {
    return Math.max(max, steps.indexOf(event.step));
  }
  return max;
}, -1);

const progressPercent = currentStepIndex >= 0 
  ? ((currentStepIndex + 1) / steps.length) * 100 
  : 0;

// Get current step label
const getCurrentStepLabel = () => {
  const lastEvent = events[events.length - 1];
  if (!lastEvent) return 'Starting...';
  
  const labels = {
    scraping: 'Fetching job description...',
    parsing: 'Analyzing requirements...',
    tailoring: 'Rewriting resume...',
    compiling: 'Generating PDF...',
  };
  
  if (lastEvent.type === 'step_started' && lastEvent.step) {
    return labels[lastEvent.step as keyof typeof labels] || lastEvent.step;
  }
  
  if (lastEvent.type === 'retry_attempt') {
    return `Retrying (attempt ${lastEvent.data?.attempt || 1})...`;
  }
  
  return 'Processing...';
};

// Render in UI:
{job.status === 'processing' && (
  <div className="space-y-4">
    <div className="flex items-center gap-3">
      <Loader2 className="h-5 w-5 animate-spin text-primary" />
      <span className="text-sm font-medium">{getCurrentStepLabel()}</span>
    </div>
    
    <Progress value={progressPercent} className="h-2" />
    
    {/* Step checklist */}
    <div className="space-y-2 mt-4">
      {steps.map((step, idx) => {
        const isCompleted = events.some(
          e => e.type === 'step_completed' && e.step === step
        );
        const isActive = currentStepIndex === idx;
        const isFailed = events.some(
          e => e.type === 'step_failed' && e.step === step
        );
        
        return (
          <div key={step} className="flex items-center gap-2 text-sm">
            {isCompleted ? (
              <CheckCircle2 className="h-4 w-4 text-green-500" />
            ) : isFailed ? (
              <AlertCircle className="h-4 w-4 text-red-500" />
            ) : isActive ? (
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
            ) : (
              <Circle className="h-4 w-4 text-muted-foreground" />
            )}
            <span className={isActive ? 'font-medium' : 'text-muted-foreground'}>
              {step.charAt(0).toUpperCase() + step.slice(1)}
            </span>
          </div>
        );
      })}
    </div>
    
    {/* Show retry warnings */}
    {events.some(e => e.type === 'retry_attempt') && (
      <div className="text-xs text-amber-600 flex items-center gap-2">
        <AlertCircle className="h-3 w-3" />
        System is retrying due to validation issues
      </div>
    )}
  </div>
)}
```

---

### 4.7 Manual Retry Button

**Backend Endpoint:**

```python
@app.post("/jobs/{job_id}/retry")
async def retry_job(job_id: int, background_tasks: BackgroundTasks):
    """Retry a failed job."""
    with Session(engine) as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        if job.status not in ["failed", "dismissed"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot retry job with status: {job.status}"
            )
        
        # Reset job to processing
        job.status = "processing"
        job.error_message = None
        session.add(job)
        session.commit()
        
        # Restart pipeline
        background_tasks.add_task(process_application, job.id, job.url)
        
        return {"message": "Job retry started", "job_id": job.id}
```

**Frontend Button:**

```typescript
const [retrying, setRetrying] = useState(false);

async function handleRetry() {
  setRetrying(true);
  try {
    await fetch(`${apiUrl}/jobs/${id}/retry`, { method: 'POST' });
    window.location.reload(); // Reload to show processing state
  } catch (err) {
    console.error('Retry failed:', err);
  } finally {
    setRetrying(false);
  }
}

// In render:
{job.status === 'failed' && (
  <Button onClick={handleRetry} disabled={retrying}>
    {retrying ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Retry Application'}
  </Button>
)}
```

---

## 5. Database Schema Changes

**New Migration:** `005_add_retry_tracking.py`

```python
"""Add retry tracking to jobs

Revision ID: 005
Revises: 004
Create Date: 2026-04-04
"""

from alembic import op
import sqlalchemy as sa

def upgrade():
    # Add retry_count column to track automatic retry attempts
    op.add_column('job', sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'))

def downgrade():
    op.drop_column('job', 'retry_count')
```

**Update `database.py`:**

```python
class Job(SQLModel, table=True):
    """Represents a job application or suggestion."""
    id: Optional[int] = Field(default=None, primary_key=True)
    url: str
    company: str
    title: str
    status: str = "suggested"
    requirements: Optional[str] = None
    pdf_path: Optional[str] = None
    score: Optional[int] = None
    source_id: Optional[int] = Field(default=None, foreign_key="jobsource.id")
    error_message: Optional[str] = None
    retry_count: int = 0  # NEW: Track automatic retry attempts
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
```

**Track Retries in `process_application`:**

```python
# Before retry loop:
job.retry_count = 0
session.add(job)
session.commit()

# In retry loop:
if attempt > 1:
    job.retry_count = attempt - 1
    session.add(job)
    session.commit()
```

---

## 6. Environment Variables

**New Variables:**

```bash
# Hook Configuration
AGENT_HOOKS_ENABLED=true
PRE_TAILOR_HOOKS=validate_master_resume_exists
POST_TAILOR_HOOKS=validate_tailored_latex,log_agent_output
POST_SCORE_HOOKS=warn_on_low_score

# Retry Configuration
MAX_RETRIES=3

# SSE Configuration (optional)
SSE_KEEPALIVE_INTERVAL=30  # seconds
```

---

## 7. Testing Strategy

### Unit Tests

**Test Event Bus:**
```python
# tests/test_event_bus.py
async def test_event_emission():
    bus = EventBus()
    await bus.create_job_queue(1)
    
    event = JobEvent(
        type=EventType.STEP_STARTED,
        timestamp=datetime.utcnow(),
        job_id=1,
        step="scraping"
    )
    await bus.emit(event)
    
    queue = await bus.get_job_queue(1)
    received = await queue.get()
    
    assert received.type == EventType.STEP_STARTED
    assert received.step == "scraping"
```

**Test Hooks:**
```python
# tests/test_hooks.py
def test_validate_latex_hook():
    hook = ValidateTailoredLatex()
    
    # Valid LaTeX
    context = HookContext(
        agent_name="test",
        job_id=1,
        input_data={},
        output_data="\\documentclass{article}\n\\begin{document}\nHello\\end{document}"
    )
    result, error = hook.execute(context)
    assert result == HookResult.ALLOW
    
    # Invalid LaTeX (unclosed brace)
    context.output_data = "\\documentclass{article\n\\begin{document}\nHello\\end{document}"
    result, error = hook.execute(context)
    assert result == HookResult.DENY
    assert "brace" in error.lower()
```

**Test Health Checks:**
```python
# tests/test_startup.py
async def test_gemini_api_key_check():
    # Missing key
    os.environ.pop("GOOGLE_API_KEY", None)
    check = GeminiAPIKeyCheck()
    result = await check.check()
    assert not result.passed
    
    # Key present
    os.environ["GOOGLE_API_KEY"] = "test-key"
    result = await check.check()
    assert result.passed
```

### Integration Tests

**Test Full Pipeline with Events:**
```python
# tests/integration/test_pipeline.py
async def test_pipeline_emits_all_events():
    # Create test job
    job_id = create_test_job()
    
    # Collect events
    collected_events = []
    queue = await event_bus.create_job_queue(job_id)
    
    # Start pipeline
    asyncio.create_task(process_application(job_id, "http://test.com"))
    
    # Collect events until completion
    while True:
        event = await queue.get()
        collected_events.append(event)
        if event.type in [EventType.PIPELINE_COMPLETED, EventType.PIPELINE_FAILED]:
            break
    
    # Verify event sequence
    event_types = [e.type for e in collected_events]
    assert EventType.PIPELINE_STARTED in event_types
    assert EventType.STEP_STARTED in event_types
    assert EventType.HOOK_VALIDATED in event_types
```

### Manual Testing Checklist

- [ ] Start server without GOOGLE_API_KEY → should fail to start
- [ ] Start server without pdflatex → should fail to start
- [ ] POST /apply with valid URL → see progress events in browser Network tab
- [ ] Simulate bad LaTeX output → verify retry attempts appear
- [ ] Click "Retry" button on failed job → verify job restarts
- [ ] Check `/health` endpoint → all checks should pass
- [ ] View job details during processing → see step-by-step progress
- [ ] Scraper unreachable → jobs should fail gracefully (non-critical check)

---

## 8. Rollout Plan

### Phase 1: Core Infrastructure (Week 1)
- Implement `core/event_bus.py`
- Add event emission to `process_application` (no hooks yet)
- Add SSE endpoint `/jobs/{id}/stream`
- Basic frontend SSE integration with progress display

### Phase 2: Hook System (Week 2)
- Implement `core/hooks.py` with 4 built-in hooks
- Integrate hook runner into pipeline
- Add retry logic for hook failures
- Test with intentionally broken LaTeX

### Phase 3: Health Checks (Week 3)
- Implement `core/startup.py` with 6 health checks
- Add startup integration to `server.py` lifespan
- Add `/health` endpoint
- Add manual retry endpoint `/jobs/{id}/retry`

### Phase 4: Frontend Polish (Week 4)
- Enhanced progress UI with step checklist
- Retry attempt indicators
- Manual retry button
- Health check warning banner (if non-critical checks fail)

### Phase 5: Testing & Docs (Week 5)
- Write unit tests for all components
- Integration tests for full pipeline
- Update README with new features
- Update `.env.example` with new variables

---

## 9. Success Metrics

**Reliability Metrics:**
- Failed jobs due to bad LaTeX drops by 80%
- Startup misconfiguration detected in <5 seconds (vs. at runtime)
- 95% of hook validation failures result in successful retry

**User Experience Metrics:**
- Users see first progress event within 1 second of applying
- No jobs spend >5 seconds in "Processing..." without update
- Manual retry recovers 60%+ of failed jobs

**Performance Metrics:**
- SSE streams add <50ms overhead per event
- Hook validation adds <500ms to total pipeline time
- Health checks complete in <3 seconds on startup

---

## 10. Future Enhancements

These features build naturally on this infrastructure:

**Audit Logging (Feature 7):**
- Events already capture timestamps, steps, inputs/outputs
- Add `audit_log` JSON column to Job table
- Serialize events to database on pipeline completion

**Token Usage Tracking (Feature 4):**
- Add token count to `step_completed` events for agent calls
- Accumulate from events and save to Job table
- Display in progress UI: "Parsing (142 tokens used)"

**Dry-Run Mode (Feature 8):**
- Add `dry_run: bool` flag to `process_application`
- Skip LLM calls but emit mock events
- Frontend shows "Preview Mode" banner

**Multi-Provider Support (Feature 3):**
- Hooks can validate provider-specific constraints
- Events include model/provider info
- Cost calculation in events varies by provider

---

## 11. Open Questions

1. **Event Retention:** How long should event queues stay in memory after job completion? (Current: 5 seconds)
2. **Hook Extensibility:** Should we support loading custom hooks from `core/hooks/custom/`? (Current: environment variable config only)
3. **Health Check Frequency:** Should `/health` re-run checks on each call or return cached startup results? (Current: cached)
4. **SSE Reconnection:** Should frontend auto-reconnect to SSE if connection drops mid-pipeline? (Current: no)
5. **Retry Backoff:** Should retry delays increase exponentially (1s, 2s, 4s) or stay fixed (1s)? (Current: fixed 1s)

---

## 12. Dependencies

**No new Python packages required** - uses existing:
- `asyncio` (built-in)
- `fastapi.responses.StreamingResponse` (already installed)

**No new npm packages required** - uses:
- `EventSource` (browser built-in)
- Existing shadcn/ui components

---

## 13. Rollback Plan

If critical issues arise:

1. **Disable Hooks:** Set `AGENT_HOOKS_ENABLED=false` → pipeline runs without validation
2. **Disable SSE:** Comment out SSE endpoint → frontend shows static "Processing..."
3. **Disable Health Checks:** Remove health check logic from lifespan → server starts without validation
4. **Revert Migration:** Downgrade migration `005` → remove `retry_count` column

Each component is independently toggleable for safe rollback.

---

## Conclusion

This Event-Driven Architecture provides a robust foundation for the top 3 essential features while setting up infrastructure that future roadmap features will leverage. The design prioritizes:

- **Decoupling** - Components communicate via events, not direct calls
- **Extensibility** - New hooks, health checks, and event consumers can be added without modifying core pipeline
- **Reliability** - Hooks catch errors early, retries recover from transient failures, health checks prevent misconfiguration
- **User Experience** - Real-time progress eliminates uncertainty during 10-30 second operations

The system is production-ready, testable, and designed for incremental rollout with safe rollback options.
