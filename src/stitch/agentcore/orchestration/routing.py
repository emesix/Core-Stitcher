"""Deterministic executor routing — maps step kinds and tags to executor preferences.

Routing is config-driven, not LLM-driven. Precedence:
1. Tag-based rules (always win)
2. Step-kind rules
3. Global default
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from stitch.agentcore.storekit.models import StepKind  # noqa: TC001  # Pydantic needs at runtime


class EscalationTrigger(StrEnum):
    VERDICT_REJECT = "verdict_reject"
    SCHEMA_INVALID = "schema_invalid"
    RETRY_EXHAUSTED = "retry_exhausted"
    CONTEXT_EXCEEDED = "context_exceeded"


class RoutingRule(BaseModel):
    """A single routing rule mapping step kinds and/or tags to executor preferences."""

    step_kinds: list[StepKind] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    primary: str
    fallback_chain: list[str] = Field(default_factory=list)
    escalation_target: str | None = None
    escalation_triggers: list[EscalationTrigger] = Field(default_factory=list)
    allow_escalation: bool = True
    fail_closed: bool = False


class RoutingDecision(BaseModel, frozen=True):
    """The result of a routing lookup."""

    primary: str
    fallback_chain: list[str] = Field(default_factory=list)
    escalation_target: str | None = None
    escalation_triggers: list[EscalationTrigger] = Field(default_factory=list)
    allow_escalation: bool = True
    fail_closed: bool = False
    matched_rule: int | None = None


class RoutingPolicy(BaseModel):
    """Deterministic routing policy — maps step kinds and tags to executor preferences."""

    rules: list[RoutingRule] = Field(default_factory=list)
    default_primary: str = "local-gpu"
    default_fallback: str = "openrouter"

    def resolve(self, kind: StepKind, effective_tags: list[str]) -> RoutingDecision:
        """Find the best matching rule for a given step kind and tags.

        Precedence: tag-based rules > step-kind rules > global default.
        """
        # Pass 1: tag-based rules (always win)
        for i, rule in enumerate(self.rules):
            if rule.tags and any(t in effective_tags for t in rule.tags):
                return self._decision_from_rule(rule, i)

        # Pass 2: step-kind rules
        for i, rule in enumerate(self.rules):
            if rule.step_kinds and kind in rule.step_kinds:
                return self._decision_from_rule(rule, i)

        # Pass 3: global default
        return RoutingDecision(
            primary=self.default_primary,
            fallback_chain=[self.default_fallback],
        )

    def _decision_from_rule(self, rule: RoutingRule, index: int) -> RoutingDecision:
        return RoutingDecision(
            primary=rule.primary,
            fallback_chain=rule.fallback_chain,
            escalation_target=rule.escalation_target,
            escalation_triggers=rule.escalation_triggers,
            allow_escalation=rule.allow_escalation,
            fail_closed=rule.fail_closed,
            matched_rule=index,
        )


def alpha_routing_policy() -> RoutingPolicy:
    """The approved alpha routing table from the spec."""
    from stitch.agentcore.storekit.models import StepKind

    return RoutingPolicy(
        rules=[
            # Tag overrides — always win
            RoutingRule(
                tags=["high_risk", "write_path"],
                primary="openrouter",
                fallback_chain=[],
                allow_escalation=False,
                fail_closed=True,
            ),
            # Summary: lightweight, CPU can handle plain-text output
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY],
                primary="local-gpu",
                fallback_chain=["local-cpu"],
                escalation_target="openrouter",
                escalation_triggers=[
                    EscalationTrigger.SCHEMA_INVALID,
                ],
                allow_escalation=True,
            ),
            # Review: requires structured JSON output, CPU is not reliable for this
            RoutingRule(
                step_kinds=[StepKind.AI_REVIEW],
                primary="local-gpu",
                fallback_chain=[],
                escalation_target="openrouter",
                escalation_triggers=[
                    EscalationTrigger.VERDICT_REJECT,
                    EscalationTrigger.SCHEMA_INVALID,
                ],
                allow_escalation=True,
                fail_closed=True,
            ),
            # Corrections need stronger reasoning
            RoutingRule(
                step_kinds=[StepKind.CORRECTION],
                primary="openrouter",
                fallback_chain=[],
                allow_escalation=False,
            ),
            # Compute tasks go to sidecar, no LLM fallback
            RoutingRule(
                step_kinds=[StepKind.COMPUTE_TASK],
                primary="local-sidecar",
                fallback_chain=[],
                allow_escalation=False,
                fail_closed=True,
            ),
        ],
    )
