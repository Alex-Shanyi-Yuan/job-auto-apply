from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from core.event_bus import EventType, JobEvent
from database import utcnow


class HookResult(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


@dataclass
class HookContext:
    job_id: int
    step: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class HookDecision:
    result: HookResult
    message: Optional[str] = None


@dataclass
class HookRunSummary:
    denied: bool = False
    message: Optional[str] = None
    warnings: list[str] = field(default_factory=list)


class Hook(ABC):
    name: str

    @abstractmethod
    def evaluate(self, context: HookContext) -> HookDecision:
        raise NotImplementedError


class MasterResumeValidationHook(Hook):
    name = "master-resume-validation"

    def evaluate(self, context: HookContext) -> HookDecision:
        master_latex = str(context.payload.get("master_latex", ""))
        if not master_latex.strip():
            return HookDecision(HookResult.DENY, "Master resume is empty")
        if r"\begin{document}" not in master_latex or r"\end{document}" not in master_latex:
            return HookDecision(HookResult.DENY, "Master resume missing LaTeX document markers")
        return HookDecision(HookResult.ALLOW, "Master resume validated")


class TailoredLatexValidationHook(Hook):
    name = "tailored-latex-validation"

    def evaluate(self, context: HookContext) -> HookDecision:
        tailored_latex = str(context.payload.get("tailored_latex", ""))
        if "```" in tailored_latex:
            return HookDecision(HookResult.DENY, "Tailored LaTeX contains markdown fence artifacts")
        if r"\begin{document}" not in tailored_latex or r"\end{document}" not in tailored_latex:
            return HookDecision(HookResult.DENY, "Tailored LaTeX missing LaTeX document markers")
        if _has_unbalanced_braces(tailored_latex):
            return HookDecision(HookResult.DENY, "Tailored LaTeX has unbalanced braces")
        return HookDecision(HookResult.ALLOW, "Tailored LaTeX validated")


class TailoredLatexObservabilityHook(Hook):
    name = "tailored-latex-observability"

    def evaluate(self, context: HookContext) -> HookDecision:
        master_latex = str(context.payload.get("master_latex", ""))
        tailored_latex = str(context.payload.get("tailored_latex", ""))
        if master_latex and tailored_latex and len(tailored_latex) < max(50, int(len(master_latex) * 0.25)):
            return HookDecision(HookResult.WARN, "Tailored LaTeX length is significantly shorter than master resume")
        return HookDecision(HookResult.ALLOW, "Observability check passed")


class WarnOnLowScoreHook(Hook):
    name = "warn-on-low-score"

    def __init__(self, threshold: int = 30):
        self.threshold = threshold

    def evaluate(self, context: HookContext) -> HookDecision:
        score = context.payload.get("score")
        if score is None:
            return HookDecision(HookResult.ALLOW, "No score supplied")
        try:
            normalized_score = int(score)
        except (TypeError, ValueError):
            return HookDecision(HookResult.WARN, "Score is not numeric")
        if normalized_score < self.threshold:
            return HookDecision(HookResult.WARN, f"Low score detected: {normalized_score}")
        return HookDecision(HookResult.ALLOW, "Score above threshold")


class LogAgentOutputHook(Hook):
    name = "log-agent-output"

    def evaluate(self, context: HookContext) -> HookDecision:
        output_summary = context.payload.get("output_summary")
        if output_summary is None:
            output_summary = context.payload.get("tailored_latex")
        summary_text = str(output_summary)[:200]
        return HookDecision(HookResult.ALLOW, f"Output summary: {summary_text}")


class AgentHookRunner:
    def __init__(self, event_bus):
        self._event_bus = event_bus

    async def run_pre_hooks(self, job_id: int, step: str, hooks: list[Hook], payload: Optional[dict[str, Any]] = None) -> HookRunSummary:
        return await self._run_hooks(job_id=job_id, step=step, hooks=hooks, payload=payload or {})

    async def run_post_hooks(self, job_id: int, step: str, hooks: list[Hook], payload: Optional[dict[str, Any]] = None) -> HookRunSummary:
        return await self._run_hooks(job_id=job_id, step=step, hooks=hooks, payload=payload or {})

    async def _run_hooks(self, job_id: int, step: str, hooks: list[Hook], payload: dict[str, Any]) -> HookRunSummary:
        summary = HookRunSummary()
        context = HookContext(job_id=job_id, step=step, payload=payload)

        for hook in hooks:
            await self._emit(EventType.HOOK_STARTED, job_id, step, hook.name)
            decision = hook.evaluate(context)
            if decision.result == HookResult.ALLOW:
                await self._emit(EventType.HOOK_VALIDATED, job_id, step, hook.name, decision.message)
                continue
            if decision.result == HookResult.WARN:
                if decision.message:
                    summary.warnings.append(decision.message)
                await self._emit(EventType.HOOK_WARNED, job_id, step, hook.name, decision.message)
                continue

            summary.denied = True
            summary.message = decision.message or f"Hook failed: {hook.name}"
            await self._emit(EventType.HOOK_FAILED, job_id, step, hook.name, summary.message)
            return summary

        return summary

    async def _emit(self, event_type: EventType, job_id: int, step: str, hook_name: str, message: Optional[str] = None):
        await self._event_bus.emit(
            JobEvent(
                type=event_type,
                timestamp=utcnow(),
                job_id=job_id,
                step=step,
                hook=hook_name,
                error=message if event_type == EventType.HOOK_FAILED else None,
                data={"message": message} if message else {},
            )
        )


def _has_unbalanced_braces(content: str) -> bool:
    brace_balance = 0
    escaped = False
    for char in content:
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == "{":
            brace_balance += 1
        elif char == "}":
            brace_balance -= 1
            if brace_balance < 0:
                return True
    return brace_balance != 0
