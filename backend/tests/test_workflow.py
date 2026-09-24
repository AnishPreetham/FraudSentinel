"""End-to-end workflow tests for all three demo scenarios."""
import pytest
import asyncio
from app.agent.workflow import run_investigation
from app.models.case import CaseStatus


@pytest.mark.asyncio
async def test_scenario_a_connected_fraud_ring():
    result = await run_investigation(
        case_id="TEST-A-001",
        customer_id="C-001",
        account_id="A-001",
        trigger={
            "type": "suspicious_transfer",
            "amount": 14450.0,
            "shared_device": True,
            "structured": True,
        },
    )
    assert result.get("error", "") == "", f"Workflow error: {result.get('error')}"
    assert result["risk_level"] in ("HIGH", "CRITICAL")
    assert "MONEY_LAUNDERING" in result.get("fraud_patterns", [])
    assert len(result.get("evidence", [])) > 0
    assert result.get("recommendation", {}).get("action") in (
        "block_account", "file_sar_report", "escalate_to_analyst"
    )
    # block_account requires analyst approval
    if result["recommendation"]["action"] == "block_account":
        assert result["recommendation"]["requires_approval"] is True


@pytest.mark.asyncio
async def test_scenario_b_ambiguous_new_customer():
    result = await run_investigation(
        case_id="TEST-B-001",
        customer_id="C-002",
        account_id="A-005",
        trigger={
            "type": "large_first_transaction",
            "amount": 8500.0,
            "kyc_pending": True,
        },
    )
    assert result.get("error", "") == "", f"Workflow error: {result.get('error')}"
    assert result.get("status") is not None
    assert result.get("recommendation", {}).get("action") is not None


@pytest.mark.asyncio
async def test_scenario_c_account_takeover():
    result = await run_investigation(
        case_id="TEST-C-001",
        customer_id="C-003",
        account_id="A-010",
        trigger={
            "type": "suspicious_login",
            "new_device": True,
            "new_geography": True,
            "location": "Eastern Europe",
            "rapid_transfers_after_login": True,
        },
    )
    assert result.get("error", "") == "", f"Workflow error: {result.get('error')}"
    assert result["risk_level"] in ("HIGH", "CRITICAL")
    assert "ACCOUNT_TAKEOVER" in result.get("fraud_patterns", [])


@pytest.mark.asyncio
async def test_workflow_produces_timeline():
    result = await run_investigation(
        case_id="TEST-TL-001",
        customer_id="C-001",
        account_id="A-001",
        trigger={"type": "test"},
    )
    timeline = result.get("timeline", [])
    step_names = [s["step"] for s in timeline]
    for expected_step in ("create_case", "graph_investigation", "collect_evidence",
                          "retrieve_history", "detect_patterns", "assess_risk"):
        assert expected_step in step_names, f"Missing step: {expected_step}"


@pytest.mark.asyncio
async def test_workflow_policy_never_auto_executes_block():
    """block_account must always require approval regardless of confidence."""
    result = await run_investigation(
        case_id="TEST-POL-001",
        customer_id="C-001",
        account_id="A-001",
        trigger={"type": "suspicious_transfer", "shared_device": True, "structured": True},
    )
    rec = result.get("recommendation", {})
    if rec.get("action") == "block_account":
        assert rec.get("requires_approval") is True, "block_account must always require approval"
        assert rec.get("execution_status") != "AUTO_EXECUTED"


@pytest.mark.asyncio
async def test_unknown_customer_completes_without_error():
    result = await run_investigation(
        case_id="TEST-UNK-001",
        customer_id="C-UNKNOWN",
        account_id="A-UNKNOWN",
        trigger={"type": "manual_review"},
    )
    # Should complete (may escalate) but not crash
    assert result.get("error", "") == ""
    assert result.get("status") is not None
