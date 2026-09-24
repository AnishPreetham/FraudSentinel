"""End-to-end workflow tests for all demo scenarios including evidence pause/resume."""
import pytest
import asyncio
from app.agent.workflow import run_investigation, resume_investigation
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


@pytest.mark.asyncio
async def test_scenario_d_triggers_awaiting_evidence():
    """Verified KYC + contradicting history creates high uncertainty on HIGH-risk case."""
    result = await run_investigation(
        case_id="TEST-D-001",
        customer_id="C-AMBIG",
        account_id="A-200",
        trigger={"type": "geography_alert", "kyc_verified_prior": True},
    )
    assert result.get("error", "") == "", f"Workflow error: {result.get('error')}"
    assert result.get("status") == CaseStatus.AWAITING_EVIDENCE, (
        f"Expected AWAITING_EVIDENCE, got {result.get('status')} "
        f"(confidence={result.get('confidence')}, risk={result.get('risk_level')})"
    )
    assert result.get("confidence", 1.0) < 0.5, "Confidence should be below 0.5 to justify pause"
    assert result.get("risk_level") in ("HIGH", "CRITICAL"), "Risk must be HIGH/CRITICAL to trigger pause"
    patterns = result.get("fraud_patterns", [])
    assert "ACCOUNT_TAKEOVER" in patterns
    missing = result.get("uncertainty", {}).get("missing_evidence", [])
    assert len(missing) > 0, "Missing evidence list must be non-empty to trigger pause"
    # Timeline must show the pause node
    step_names = [s["step"] for s in result.get("timeline", [])]
    assert "request_additional_evidence" in step_names
    assert "write_memory" not in step_names, "Memory should NOT be written before evidence pause"


@pytest.mark.asyncio
async def test_evidence_resume_after_pause():
    """Submitting evidence after AWAITING_EVIDENCE resumes and completes the investigation."""
    state = await run_investigation(
        case_id="TEST-D-RESUME-001",
        customer_id="C-AMBIG",
        account_id="A-200",
        trigger={"type": "geography_alert", "kyc_verified_prior": True},
    )
    assert state.get("status") == CaseStatus.AWAITING_EVIDENCE

    new_evidence = [{
        "evidence_id": "EV-RESUME-001",
        "evidence_type": "supporting",
        "source": "device_match",
        "content": "Customer confirmed via SMS OTP — device ownership verified",
        "reliability": 0.90,
    }]
    resumed = await resume_investigation(state, new_evidence)

    assert resumed.get("error", "") == "", f"Resume error: {resumed.get('error')}"
    assert resumed.get("status") != CaseStatus.AWAITING_EVIDENCE, "Status must change after evidence submission"
    assert resumed.get("confidence", 0) > state.get("confidence", 0), "Confidence should improve after adding supporting evidence"
    assert len(resumed.get("evidence", [])) == len(state.get("evidence", [])) + 1
    # Timeline must include the evidence_received step
    step_names = [s["step"] for s in resumed.get("timeline", [])]
    assert "evidence_received" in step_names
    assert "write_memory" in step_names, "Memory must be written after completed resume"


@pytest.mark.asyncio
async def test_evidence_deduplication():
    """Submitting the same evidence_id twice must not create duplicate entries."""
    state = await run_investigation(
        case_id="TEST-D-DEDUP-001",
        customer_id="C-AMBIG",
        account_id="A-200",
        trigger={"type": "geography_alert", "kyc_verified_prior": True},
    )
    assert state.get("status") == CaseStatus.AWAITING_EVIDENCE

    evidence_item = [{
        "evidence_id": "EV-DEDUP-001",
        "evidence_type": "supporting",
        "source": "device_match",
        "content": "OTP verified",
        "reliability": 0.90,
    }]
    resumed = await resume_investigation(state, evidence_item)
    count_after_first = len(resumed.get("evidence", []))

    # Submit the same evidence again
    resumed2 = await resume_investigation(resumed, evidence_item)
    count_after_second = len(resumed2.get("evidence", []))

    assert count_after_second == count_after_first, (
        f"Deduplication failed: evidence count went from {count_after_first} to {count_after_second}"
    )
