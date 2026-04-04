# tests/test_event_bus.py
import pytest
import asyncio
from datetime import datetime
from core.event_bus import EventBus, JobEvent, EventType

@pytest.mark.asyncio
async def test_create_job_queue():
    """Test creating a queue for a specific job."""
    bus = EventBus()
    queue = await bus.create_job_queue(job_id=1)
    
    assert queue is not None
    assert isinstance(queue, asyncio.Queue)
    
    # Should return same queue if called again
    queue2 = await bus.create_job_queue(job_id=1)
    assert queue is queue2

@pytest.mark.asyncio
async def test_emit_event_to_job_queue():
    """Test emitting an event to a job's queue."""
    bus = EventBus()
    await bus.create_job_queue(job_id=1)
    
    event = JobEvent(
        type=EventType.STEP_STARTED,
        timestamp=datetime.utcnow(),
        job_id=1,
        step="scraping"
    )
    
    await bus.emit(event)
    
    queue = await bus.get_job_queue(job_id=1)
    received = await queue.get()
    
    assert received.type == EventType.STEP_STARTED
    assert received.step == "scraping"
    assert received.job_id == 1

@pytest.mark.asyncio
async def test_cleanup_job_queue():
    """Test removing a job's queue after completion."""
    bus = EventBus()
    await bus.create_job_queue(job_id=1)
    
    await bus.cleanup_job_queue(job_id=1)
    
    queue = await bus.get_job_queue(job_id=1)
    assert queue is None
