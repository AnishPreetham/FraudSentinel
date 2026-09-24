"""Tests for the deterministic policy engine."""
import pytest
from app.agent.policy import validate_action, is_auto_executable, get_required_approver


def test_block_account_requires_approval():
    decision = validate_action("block_account", confidence=0.85, risk_level="HIGH")
    assert decision.allowed is True
    assert decision.requires_approval is True
    assert decision.approver_role == "FRAUD_ANALYST"
    assert decision.auto_executable is False


def test_block_account_critical_always_requires_approval():
    decision = validate_action("block_account", confidence=0.99, risk_level="CRITICAL")
    assert decision.requires_approval is True


def test_monitor_account_auto_execute_above_threshold():
    decision = validate_action("monitor_account", confidence=0.6, risk_level="MEDIUM")
    assert decision.allowed is True
    assert decision.auto_executable is True
    assert decision.requires_approval is False


def test_monitor_account_below_confidence_requires_approval():
    decision = validate_action("block_account", confidence=0.4, risk_level="HIGH")
    # confidence 0.4 < min_confidence 0.7 for block_account
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_unknown_action_denied():
    decision = validate_action("delete_everything", confidence=0.99, risk_level="LOW")
    assert decision.allowed is False
    assert decision.requires_approval is True


def test_allow_transaction_auto():
    decision = validate_action("allow_transaction", confidence=0.9, risk_level="LOW")
    assert decision.allowed is True
    assert decision.auto_executable is True


def test_file_sar_report_requires_compliance():
    decision = validate_action("file_sar_report", confidence=0.8, risk_level="HIGH")
    assert decision.requires_approval is True
    assert decision.approver_role == "COMPLIANCE_OFFICER"


def test_get_required_approver():
    assert get_required_approver("block_account") == "FRAUD_ANALYST"
    assert get_required_approver("file_sar_report") == "COMPLIANCE_OFFICER"
    assert get_required_approver("monitor_account") is None


def test_is_auto_executable():
    assert is_auto_executable("monitor_account", 0.6) is True
    assert is_auto_executable("block_account", 0.99) is False  # always requires approval
    assert is_auto_executable("allow_transaction", 0.1) is True


def test_critical_risk_non_approval_action_gets_override():
    # warn_customer has no approval requirement normally, but CRITICAL overrides
    decision = validate_action("warn_customer", confidence=0.8, risk_level="CRITICAL")
    assert decision.requires_approval is True
