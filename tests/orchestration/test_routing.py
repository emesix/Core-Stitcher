"""Tests for deterministic routing policy — precedence, matching, fallback vs escalation."""

from __future__ import annotations

from stitch.agentcore.orchestration.routing import (
    EscalationTrigger,
    RoutingPolicy,
    RoutingRule,
    alpha_routing_policy,
)
from stitch.agentcore.storekit.models import StepKind

# --- Precedence ---


def test_tag_rules_beat_step_kind_rules():
    """Tag-based rules always win over step-kind rules."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(tags=["high_risk"], primary="external"),
            RoutingRule(step_kinds=[StepKind.AI_SUMMARY], primary="local-gpu"),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, ["high_risk"])
    assert decision.primary == "external"
    assert decision.matched_rule == 0


def test_step_kind_matches_when_no_tag_match():
    """Step-kind rule fires when no tag rule matches."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(tags=["high_risk"], primary="external"),
            RoutingRule(step_kinds=[StepKind.AI_SUMMARY], primary="local-gpu"),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, [])
    assert decision.primary == "local-gpu"
    assert decision.matched_rule == 1


def test_global_default_when_no_rule_matches():
    """Global default fires when no rule matches."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(step_kinds=[StepKind.AI_SUMMARY], primary="local-gpu"),
        ],
        default_primary="fallback-exec",
        default_fallback="cloud",
    )
    decision = policy.resolve(StepKind.CORRECTION, [])
    assert decision.primary == "fallback-exec"
    assert decision.fallback_chain == ["cloud"]
    assert decision.matched_rule is None


def test_first_tag_rule_wins():
    """When multiple tag rules match, first one wins."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(tags=["high_risk"], primary="external-a"),
            RoutingRule(tags=["high_risk"], primary="external-b"),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, ["high_risk"])
    assert decision.primary == "external-a"


def test_any_tag_triggers_match():
    """A tag rule matches if ANY of its tags are in the effective tags."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(tags=["write_path", "high_risk"], primary="external"),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, ["write_path"])
    assert decision.primary == "external"


# --- Decision properties ---


def test_decision_carries_fallback_chain():
    policy = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY],
                primary="local-gpu",
                fallback_chain=["local-cpu", "cloud"],
            ),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, [])
    assert decision.fallback_chain == ["local-cpu", "cloud"]


def test_decision_carries_escalation_info():
    policy = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_REVIEW],
                primary="local-gpu",
                escalation_target="openrouter",
                escalation_triggers=[EscalationTrigger.VERDICT_REJECT],
                allow_escalation=True,
            ),
        ],
    )
    decision = policy.resolve(StepKind.AI_REVIEW, [])
    assert decision.escalation_target == "openrouter"
    assert EscalationTrigger.VERDICT_REJECT in decision.escalation_triggers
    assert decision.allow_escalation is True


def test_fail_closed_propagated():
    policy = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.COMPUTE_TASK],
                primary="sidecar",
                fail_closed=True,
            ),
        ],
    )
    decision = policy.resolve(StepKind.COMPUTE_TASK, [])
    assert decision.fail_closed is True


# --- Fallback vs escalation ---


def test_fallback_and_escalation_are_separate():
    """Fallback chain and escalation target are independent concepts."""
    policy = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.AI_SUMMARY],
                primary="local-gpu",
                fallback_chain=["local-cpu"],
                escalation_target="openrouter",
                escalation_triggers=[EscalationTrigger.VERDICT_REJECT],
            ),
        ],
    )
    decision = policy.resolve(StepKind.AI_SUMMARY, [])
    # Fallback is for availability
    assert decision.fallback_chain == ["local-cpu"]
    # Escalation is for quality
    assert decision.escalation_target == "openrouter"


def test_no_escalation_when_disabled():
    policy = RoutingPolicy(
        rules=[
            RoutingRule(
                step_kinds=[StepKind.CORRECTION],
                primary="openrouter",
                allow_escalation=False,
            ),
        ],
    )
    decision = policy.resolve(StepKind.CORRECTION, [])
    assert decision.allow_escalation is False


# --- Alpha routing policy ---


def test_alpha_policy_high_risk_tag():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_SUMMARY, ["high_risk"])
    assert decision.primary == "openrouter"
    assert decision.fail_closed is True
    assert decision.allow_escalation is False


def test_alpha_policy_write_path_tag():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_REVIEW, ["write_path"])
    assert decision.primary == "openrouter"
    assert decision.fail_closed is True


def test_alpha_policy_summary_default():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_SUMMARY, [])
    assert decision.primary == "local-gpu"
    assert "local-cpu" in decision.fallback_chain
    assert decision.escalation_target == "openrouter"


def test_alpha_policy_review_default():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_REVIEW, [])
    assert decision.primary == "local-gpu"
    assert decision.fallback_chain == []  # no CPU fallback for structured review
    assert decision.fail_closed is True
    assert decision.allow_escalation is True
    assert decision.escalation_target == "openrouter"


def test_alpha_policy_correction():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.CORRECTION, [])
    assert decision.primary == "openrouter"
    assert decision.allow_escalation is False


def test_alpha_policy_compute():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.COMPUTE_TASK, [])
    assert decision.primary == "local-sidecar"
    assert decision.fail_closed is True
    assert decision.allow_escalation is False


def test_alpha_policy_domain_call_uses_default():
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.DOMAIN_CALL, [])
    assert decision.primary == "local-gpu"  # default_primary
    assert decision.matched_rule is None


# --- Live-hardened: CPU capability boundary ---


def test_alpha_policy_summary_allows_cpu_fallback():
    """Summary is lightweight text — CPU fallback is acceptable."""
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_SUMMARY, [])
    assert "local-cpu" in decision.fallback_chain


def test_alpha_policy_review_blocks_cpu_fallback():
    """Review requires structured JSON — CPU (TinyLlama) cannot produce it reliably.

    Live-validated 2026-04-10: TinyLlama on OVMS CPU returns 400 on review
    prompts that require structured JSON output. Summary fallback works fine.
    """
    policy = alpha_routing_policy()
    decision = policy.resolve(StepKind.AI_REVIEW, [])
    assert "local-cpu" not in decision.fallback_chain
    assert decision.fail_closed is True


# --- Compute step kind ---


def test_compute_task_step_kind_exists():
    assert StepKind.COMPUTE_TASK == "compute_task"
