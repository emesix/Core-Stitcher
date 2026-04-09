"""Budget and escalation policy — controls what the orchestrator is allowed to spend."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class EscalationAction(StrEnum):
    REUSE = "reuse_same_executor"
    SWITCH = "switch_executor"
    SKIP = "skip_step"
    STOP = "stop_run"


class ExecutorTier(StrEnum):
    LOCAL = "local"
    CHEAP = "cheap"
    STANDARD = "standard"
    PREMIUM = "premium"


class BudgetPolicy(BaseModel):
    """Controls orchestrator spending and escalation behavior."""

    max_ai_steps: int = 10
    max_corrections: int = 2
    max_reviews: int = 3
    allowed_tiers: list[ExecutorTier] = Field(
        default_factory=lambda: list(ExecutorTier)
    )
    prefer_local: bool = False
    prefer_domain_specific: bool = True
    allow_ai_summary: bool = True
    allow_ai_review: bool = True

    def can_run_ai_step(self, ai_steps_so_far: int) -> bool:
        return ai_steps_so_far < self.max_ai_steps

    def can_correct(self, corrections_so_far: int) -> bool:
        return corrections_so_far < self.max_corrections

    def can_review(self, reviews_so_far: int) -> bool:
        return reviews_so_far < self.max_reviews

    def should_escalate(self, failures: int) -> EscalationAction:
        if failures == 0:
            return EscalationAction.REUSE
        if failures == 1:
            return EscalationAction.SWITCH
        if failures >= 2:
            return EscalationAction.STOP
        return EscalationAction.REUSE
