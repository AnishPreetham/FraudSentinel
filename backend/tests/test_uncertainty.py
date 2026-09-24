"""Tests for the uncertainty and evidence scoring engine."""
import pytest
from app.agent.uncertainty import (
    calculate_confidence,
    identify_missing_evidence,
    assess_uncertainty,
)
from app.models.case import Evidence


def _ev(source: str, ev_type: str = "supporting", reliability: float = 0.8) -> Evidence:
    return Evidence(
        evidence_id="test-id",
        evidence_type=ev_type,
        source=source,
        content=f"Test evidence from {source}",
        reliability=reliability,
    )


def test_empty_evidence_returns_zero():
    assert calculate_confidence([]) == 0.0


def test_single_strong_evidence_high_confidence():
    conf = calculate_confidence([_ev("graph_connection", reliability=0.95)])
    assert conf > 0.8


def test_contradicting_evidence_lowers_confidence():
    supporting = [_ev("graph_connection", reliability=0.9)]
    contradicting = [_ev("customer_statement", ev_type="contradicting", reliability=0.9)]
    conf_support_only = calculate_confidence(supporting)
    conf_with_contra = calculate_confidence(supporting + contradicting)
    assert conf_with_contra < conf_support_only


def test_multiple_supporting_evidence_capped_at_1():
    many = [_ev("graph_connection", reliability=1.0) for _ in range(10)]
    assert calculate_confidence(many) <= 1.0


def test_missing_evidence_identified_for_money_laundering():
    evidence = [_ev("graph_connection"), _ev("transaction_pattern")]
    missing = identify_missing_evidence(evidence, ["MONEY_LAUNDERING"])
    # velocity is required for MONEY_LAUNDERING and not present
    assert any("velocity" in m.lower() or "transaction velocity" in m.lower() for m in missing)


def test_no_missing_when_all_present():
    evidence = [
        _ev("graph_connection"),
        _ev("transaction_pattern"),
        _ev("velocity"),
    ]
    missing = identify_missing_evidence(evidence, ["MONEY_LAUNDERING"])
    assert missing == []


def test_assess_uncertainty_returns_correct_level():
    strong_evidence = [_ev("graph_connection", reliability=0.95)] * 4
    result = assess_uncertainty(strong_evidence, ["MONEY_LAUNDERING"])
    # High support, should be LOW or MEDIUM uncertainty
    assert result.uncertainty_level in ("LOW", "MEDIUM")
    assert result.confidence > 0.5


def test_assess_uncertainty_high_with_no_evidence():
    result = assess_uncertainty([], ["ACCOUNT_TAKEOVER"])
    assert result.uncertainty_level == "HIGH"
    assert result.confidence < 0.2
