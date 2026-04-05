import asyncio
from types import SimpleNamespace

import pytest

from core.event_bus import EventBus, EventType
from core.hooks import (
    AgentHookRunner,
    Hook,
    HookContext,
    HookDecision,
    HookResult,
    MasterResumeValidationHook,
    TailoredLatexValidationHook,
)


def test_master_resume_validation_denies_missing_document_markers():
    hook = MasterResumeValidationHook()
    context = HookContext(job_id=1, step="tailoring", payload={"master_latex": r"\section{Experience}"})

    result = hook.evaluate(context)

    assert result.result == HookResult.DENY
    assert "document markers" in result.message.lower()


def test_tailored_latex_validation_denies_markdown_fences():
    hook = TailoredLatexValidationHook()
    context = HookContext(
        job_id=1,
        step="tailoring",
        payload={"tailored_latex": "```latex\n\\begin{document}\nHi\n\\end{document}\n```"},
    )

    result = hook.evaluate(context)

    assert result.result == HookResult.DENY
    assert "markdown fence" in result.message.lower()


def test_tailored_latex_validation_denies_unbalanced_braces():
    hook = TailoredLatexValidationHook()
    context = HookContext(
        job_id=1,
        step="tailoring",
        payload={"tailored_latex": "\\begin{document}\\section{X\\end{document}"},
    )

    result = hook.evaluate(context)

    assert result.result == HookResult.DENY
    assert "unbalanced braces" in result.message.lower()


class _WarnHook(Hook):
    name = "warn-hook"

    def evaluate(self, context: HookContext) -> HookDecision:
        return HookDecision(result=HookResult.WARN, message="warned")


class _DenyHook(Hook):
    name = "deny-hook"

    def evaluate(self, context: HookContext) -> HookDecision:
        return HookDecision(result=HookResult.DENY, message="denied")


@pytest.mark.asyncio
async def test_agent_hook_runner_emits_warn_and_deny_events():
    bus = EventBus()
    await bus.create_job_queue(7)
    runner = AgentHookRunner(bus)

    summary = await runner.run_post_hooks(
        job_id=7,
        step="tailoring",
        hooks=[_WarnHook(), _DenyHook()],
        payload={"tailored_latex": "\\begin{document}ok\\end{document}"},
    )

    queue = await bus.get_job_queue(7)
    event_types = []
    while not queue.empty():
        event_types.append((await queue.get()).type)

    assert summary.denied is True
    assert summary.message == "denied"
    assert EventType.HOOK_STARTED in event_types
    assert EventType.HOOK_WARNED in event_types
    assert EventType.HOOK_FAILED in event_types
