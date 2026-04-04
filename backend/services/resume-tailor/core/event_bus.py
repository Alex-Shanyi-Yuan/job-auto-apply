# core/event_bus.py
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
from enum import Enum
import asyncio

class EventType(str, Enum):
    """Types of events that can occur in the pipeline."""
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
