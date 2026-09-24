"""Tests for the next-best-action engine."""
import pytest
from app.agent.actions import determine_next_action


def _action(risk_score=0.5, risk_level="MEDIUM", confidence=0.7, patterns=None, evidence=None, needs_more=False):
    return determine_next_action(
        risk_score=risk_score,
        risk_level=risk_level,
        confidence=confidence,
        fraud_patterns=patterns or [],
        evidence_list=evidence or [],
        needs_more_evidence=needs_more,
    )


def test_money_laundering_high_confidence_block():
    result = _action(risk_level="CRITICAL", confidence=0.75, patterns=["MONEY_LAUNDERING"])
    assert result["action"] == "block_account"
    assert result["policy_decision"]["requires_approval"] is True


def test_money_laundering_medium_confidence_sar():
    result = _action(risk_level="HIGH", confidence=0.55, patterns=["MONEY_LAUNDERING"])
    assert result["action"] == "file_sar_report"


def test_account_takeover_high_confidence_block():
    result = _action(risk_level="CRITICAL", confidence=0.80, patterns=["ACCOUNT_TAKEOVER"])
    assert result["action"] == "block_account"


def test_account_takeover_medium_confidence_escalate():
    result = _action(risk_level="HIGH", confidence=0.60, patterns=["ACCOUNT_TAKEOVER"])
    assert result["action"] == "escalate_to_analyst"


def test_account_takeover_low_confidence_step_up():
    result = _action(risk_level="HIGH", confidence=0.30, patterns=["ACCOUNT_TAKEOVER"])
    assert result["action"] == "step_up_authentication"


def test_needs_more_evidence_returns_step_up():
    result = _action(needs_more=True, patterns=["MONEY_LAUNDERING"])
    assert result["action"] == "step_up_authentication"


def test_low_risk_allows_transaction():
    result = _action(risk_score=0.1, risk_level="LOW", confidence=0.9, patterns=[])
    assert result["action"] == "allow_transaction"


def test_medium_risk_monitor():
    result = _action(risk_score=0.5, risk_level="MEDIUM", confidence=0.75, patterns=[])
    assert result["action"] == "monitor_account"


def test_action_includes_policy_decision():
    result = _action(risk_level="HIGH", confidence=0.8, patterns=["VELOCITY_ABUSE"])
    assert "policy_decision" in result
    assert "requires_approval" in result["policy_decision"]
    assert "policy_basis" in result["policy_decision"]
