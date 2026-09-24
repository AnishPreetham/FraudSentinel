import uuid
import json
import os
from datetime import datetime
from typing import TypedDict, Annotated
import operator

from langgraph.graph import StateGraph, END

from app.agent import tools as agent_tools
from app.agent.uncertainty import assess_uncertainty
from app.agent.actions import determine_next_action
from app.models.case import Evidence, RiskLevel, CaseStatus, FraudPattern
from app.db.database import AsyncSessionLocal
from app.memory.case_memory import store_case_memory, find_similar_cases as db_find_similar_cases
from app.agent.llm import synthesize_case_summary
from app.graph.tigergraph import TigerGraphClient

_tg_client_wf = TigerGraphClient()


class InvestigationState(TypedDict):
    case_id: str
    customer_id: str
    account_id: str
    trigger: dict
    graph_data: dict
    transactions: list
    evidence: list
    similar_cases: list
    fraud_patterns: list
    risk_score: float
    risk_level: str
    confidence: float
    uncertainty: dict
    needs_more_evidence: bool
    evidence_requests: list
    additional_evidence: list
    recommendation: dict
    approval_status: str
    reasoning: str
    timeline: Annotated[list, operator.add]
    iteration_count: int
    status: str
    error: str


def _ts():
    return datetime.utcnow().isoformat()


def _step(name: str, description: str, data: dict = None) -> dict:
    return {
        "step": name,
        "description": description,
        "timestamp": _ts(),
        "data": data or {}
    }


async def create_case_node(state: InvestigationState) -> dict:
    return {
        "status": CaseStatus.INVESTIGATING,
        "iteration_count": 0,
        "evidence": [],
        "fraud_patterns": [],
        "evidence_requests": [],
        "additional_evidence": [],
        "timeline": [_step("create_case", f"Investigation started for customer {state['customer_id']}")],
    }


async def graph_investigation_node(state: InvestigationState) -> dict:
    customer_result = await agent_tools.investigate_customer(state["customer_id"])
    entity_result = await agent_tools.find_connected_entities(state["customer_id"])

    graph_data = {
        **customer_result.get("result", {}),
        **entity_result.get("result", {}),
        "is_mock": customer_result.get("is_mock", True)
    }

    evidence = []
    res = customer_result.get("result", {})
    if res.get("suspicious_connections"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "graph_connection",
            "content": f"{len(res['suspicious_connections'])} suspicious connected accounts found via shared device",
            "reliability": 0.90
        })
    if res.get("risk_signals"):
        for sig in res.get("risk_signals", []):
            evidence.append({
                "evidence_id": str(uuid.uuid4()),
                "evidence_type": "supporting",
                "source": "graph_connection",
                "content": f"Risk signal from graph: {sig.replace('_', ' ')}",
                "reliability": 0.80
            })

    return {
        "graph_data": graph_data,
        "evidence": state.get("evidence", []) + evidence,
        "timeline": [_step("graph_investigation", "TigerGraph neighborhood traversal complete",
                            {"suspicious_connections": len(res.get("suspicious_connections", []))})],
    }


async def collect_evidence_node(state: InvestigationState) -> dict:
    tx_result = await agent_tools.get_transaction_history(state["account_id"])
    tx_data = tx_result.get("result", {})

    evidence = []
    transactions = tx_data.get("transactions", [])

    # Detect structured amounts (below reporting threshold, multiple txns)
    amounts = [t.get("amount", 0) for t in transactions]
    structured = len(transactions) >= 2 and all(a < 5000 for a in amounts) and amounts
    if structured or tx_data.get("structured_amounts"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "transaction_pattern",
            "content": f"Structured amounts detected: {len(transactions)} transactions totaling ${tx_data.get('total_amount', 0):.0f} (all below $5,000 reporting threshold)",
            "reliability": 0.88
        })
    if tx_data.get("velocity_flag"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "velocity",
            "content": f"High transaction velocity: {tx_data.get('count', 0)} transactions in monitoring window",
            "reliability": 0.80
        })

    # Add velocity evidence if multiple large rapid transfers (ATO indicator)
    if len(transactions) >= 2 and tx_data.get("max_amount", 0) > 8000:
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "velocity",
            "content": f"Rapid high-value transfers: max ${tx_data.get('max_amount', 0):.0f} within short window",
            "reliability": 0.85
        })

    trigger = state.get("trigger", {})
    if trigger.get("new_device"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "device_match",
            "content": "Login from new/unrecognized device fingerprint — not previously associated with this customer",
            "reliability": 0.90
        })
    if trigger.get("new_geography"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "geography",
            "content": f"Transaction originating from unusual geography: {trigger.get('location', 'unknown')} — inconsistent with customer history",
            "reliability": 0.80
        })
    if trigger.get("rapid_transfers_after_login"):
        evidence.append({
            "evidence_id": str(uuid.uuid4()),
            "evidence_type": "supporting",
            "source": "transaction_pattern",
            "content": "Rapid large transfers initiated immediately after new-device login — classic ATO pattern",
            "reliability": 0.92
        })

    return {
        "transactions": tx_data.get("transactions", []),
        "evidence": state.get("evidence", []) + evidence,
        "timeline": [_step("collect_evidence", f"Collected {len(evidence)} evidence items from transactions and triggers")],
    }


async def retrieve_history_node(state: InvestigationState) -> dict:
    features = {
        "fraud_patterns": state.get("fraud_patterns", []),
        "risk_signals": state.get("graph_data", {}).get("risk_signals", []),
    }

    # Try real DB memory first; fall back to TigerGraph mock
    db_similar = []
    try:
        async with AsyncSessionLocal() as db:
            db_similar = await db_find_similar_cases(db, features, limit=5)
    except Exception:
        pass

    if db_similar:
        similar = db_similar
        source = "case_memory_db"
    else:
        result = await agent_tools.retrieve_similar_cases(features)
        similar = result.get("result", {}).get("similar_cases", [])
        source = "mock"

    return {
        "similar_cases": similar,
        "timeline": [_step("retrieve_history",
                           f"Found {len(similar)} similar historical cases (source: {source})",
                           {"source": source, "count": len(similar)})],
    }


async def detect_patterns_node(state: InvestigationState) -> dict:
    evidence = state.get("evidence", [])
    graph = state.get("graph_data", {})
    risk_signals = graph.get("risk_signals", [])
    tx_data = {
        "transactions": state.get("transactions", []),
        "structured_amounts": any(e.get("source") == "transaction_pattern" for e in evidence),
        "velocity_flag": any(e.get("source") == "velocity" for e in evidence),
        "risk_signals": risk_signals,
    }
    # Enrich graph_data with risk_signals for pattern detection
    enriched_graph = {**graph, "risk_signals": risk_signals}
    result = await agent_tools.detect_fraud_patterns(tx_data, enriched_graph)
    patterns = result.get("result", {}).get("patterns_detected", [])

    return {
        "fraud_patterns": patterns,
        "timeline": [_step("detect_patterns", f"Detected patterns: {', '.join(patterns) if patterns else 'None'}",
                            {"patterns": patterns})],
    }


async def assess_risk_node(state: InvestigationState) -> dict:
    result = await agent_tools.assess_risk(
        state.get("evidence", []),
        state.get("fraud_patterns", []),
        state.get("graph_data", {})
    )
    r = result.get("result", {})
    return {
        "risk_score": r.get("risk_score", 0.0),
        "risk_level": r.get("risk_level", "LOW"),
        "confidence": r.get("confidence", 0.0),
        "timeline": [_step("assess_risk", f"Risk assessment: {r.get('risk_level', 'LOW')} ({r.get('risk_score', 0):.0%})",
                            r)],
    }


async def assess_uncertainty_node(state: InvestigationState) -> dict:
    evidence_objects = [
        Evidence(
            evidence_id=e.get("evidence_id", str(uuid.uuid4())),
            evidence_type=e.get("evidence_type", "supporting"),
            source=e.get("source", "unknown"),
            content=e.get("content", ""),
            reliability=e.get("reliability", 0.7)
        )
        for e in state.get("evidence", [])
    ]
    assessment = assess_uncertainty(evidence_objects, state.get("fraud_patterns", []))

    needs_more = (
        assessment.confidence < 0.5
        and state.get("risk_level", "LOW") in ("HIGH", "CRITICAL")
        and state.get("iteration_count", 0) < 1
        and len(assessment.missing_evidence) > 0
    )

    return {
        "uncertainty": assessment.dict(),
        "confidence": assessment.confidence,
        "needs_more_evidence": needs_more,
        "timeline": [_step("assess_uncertainty",
                            f"Confidence: {assessment.confidence:.0%}, Uncertainty: {assessment.uncertainty_level}",
                            {"missing": assessment.missing_evidence})],
    }


def decide_evidence_sufficiency(state: InvestigationState) -> str:
    if state.get("needs_more_evidence") and state.get("iteration_count", 0) < 1:
        return "request_evidence"
    return "recommend_action"


async def request_additional_evidence_node(state: InvestigationState) -> dict:
    missing = state.get("uncertainty", {}).get("missing_evidence", [])
    requests = []
    for item in missing[:2]:
        r = await agent_tools.request_additional_evidence(
            state["case_id"], item,
            f"Required to confirm {state.get('risk_level', 'HIGH')} risk assessment"
        )
        requests.append(r.get("result", {}))

    return {
        "evidence_requests": requests,
        "needs_more_evidence": False,   # clear flag so workflow can exit cleanly
        "iteration_count": state.get("iteration_count", 0) + 1,
        "status": CaseStatus.AWAITING_EVIDENCE,
        # Workflow ends here — no auto-simulation. Frontend must POST /evidence.
        "timeline": [_step("request_additional_evidence",
                            f"Requested {len(requests)} additional evidence item(s) — case paused awaiting submission",
                            {"requests": [r.get("evidence_type", "") for r in requests]})],
    }


async def recommend_action_node(state: InvestigationState) -> dict:
    assessment = {
        "risk_score": state.get("risk_score", 0),
        "risk_level": state.get("risk_level", "LOW"),
        "confidence": state.get("confidence", 0),
        "fraud_patterns": state.get("fraud_patterns", []),
        "evidence": state.get("evidence", []),
        "needs_more_evidence": False,
    }
    result = await agent_tools.recommend_action(state["case_id"], assessment)
    rec = result.get("result", {})
    policy = rec.get("policy_decision", {})

    recommendation = {
        "action": rec.get("action", "escalate_to_analyst"),
        "reason": rec.get("reason", ""),
        "supporting_evidence": rec.get("supporting_evidence", []),
        "risk_level": state.get("risk_level", "LOW"),
        "confidence": state.get("confidence", 0),
        "remaining_uncertainty": state.get("uncertainty", {}).get("uncertainty_level", "MEDIUM"),
        "policy_basis": policy.get("policy_basis", ""),
        "requires_approval": policy.get("requires_approval", False),
        "approver_role": policy.get("approver_role"),
        "execution_status": "PENDING_APPROVAL" if policy.get("requires_approval") else
                            ("AUTO_EXECUTED" if policy.get("auto_executable") else "RECOMMENDED"),
    }

    new_status = CaseStatus.PENDING_APPROVAL if policy.get("requires_approval") else CaseStatus.ACTION_RECOMMENDED

    return {
        "recommendation": recommendation,
        "status": new_status,
        "timeline": [_step("recommend_action",
                            f"Action recommended: {recommendation['action']} ({'requires approval' if policy.get('requires_approval') else 'auto-authorized'})")],
    }


async def check_approval_node(state: InvestigationState) -> dict:
    rec = state.get("recommendation", {})
    if not rec.get("requires_approval"):
        return {
            "approval_status": "AUTO_APPROVED",
            "timeline": [_step("check_approval", "Action auto-authorized by policy engine")],
        }
    return {
        "approval_status": "PENDING",
        "timeline": [_step("check_approval", f"Waiting for {rec.get('approver_role', 'analyst')} approval")],
    }


async def execute_action_node(state: InvestigationState) -> dict:
    rec = state.get("recommendation", {})
    if state.get("approval_status") == "AUTO_APPROVED":
        executed_status = "EXECUTED"
        exec_note = f"Action '{rec.get('action')}' auto-executed by policy engine"
    else:
        executed_status = "PENDING_APPROVAL"
        exec_note = f"Action '{rec.get('action')}' awaiting analyst approval"

    updated_rec = {**rec, "execution_status": executed_status}
    return {
        "recommendation": updated_rec,
        "status": CaseStatus.ACTION_EXECUTED if executed_status == "EXECUTED" else CaseStatus.PENDING_APPROVAL,
        "timeline": [_step("execute_action", exec_note)],
    }


async def explain_decision_node(state: InvestigationState) -> dict:
    rec = state.get("recommendation", {})
    evidence = state.get("evidence", [])
    supporting = [e for e in evidence if e.get("evidence_type") == "supporting"]
    contradicting = [e for e in evidence if e.get("evidence_type") == "contradicting"]
    missing = state.get("uncertainty", {}).get("missing_evidence", [])

    result = synthesize_case_summary(
        case_id=state["case_id"],
        customer_id=state["customer_id"],
        risk_level=state.get("risk_level", "LOW"),
        risk_score=state.get("risk_score", 0.0),
        confidence=state.get("confidence", 0.0),
        fraud_patterns=state.get("fraud_patterns", []),
        supporting_evidence=supporting,
        contradicting_evidence=contradicting,
        missing_evidence=missing,
        similar_cases=state.get("similar_cases", []),
        recommendation_action=rec.get("action", "review"),
        recommendation_reason=rec.get("reason", ""),
        requires_approval=rec.get("requires_approval", False),
        approver_role=rec.get("approver_role"),
    )

    label = f"Case summary generated ({'LLM: ' + result.get('model', '') if result.get('llm_used') else 'deterministic fallback'})"
    return {
        "reasoning": result["summary"],
        "timeline": [_step("explain_decision", label, {"llm_used": result.get("llm_used")})],
    }


async def update_case_node(state: InvestigationState) -> dict:
    final_status = state.get("status", CaseStatus.RESOLVED)
    if final_status not in (CaseStatus.PENDING_APPROVAL, CaseStatus.ACTION_EXECUTED):
        final_status = CaseStatus.RESOLVED

    return {
        "status": final_status,
        "timeline": [_step("update_case", f"Case updated with final status: {final_status}")],
    }


async def write_memory_node(state: InvestigationState) -> dict:
    # Determine outcome from current status / recommendation
    status = state.get("status", "")
    action = state.get("recommendation", {}).get("action", "")
    if status == CaseStatus.CLEARED:
        outcome = "CLEARED"
    elif action in ("block_account", "freeze_and_investigate", "file_sar_report"):
        outcome = "FRAUD_CONFIRMED"
    elif action in ("allow_transaction",):
        outcome = "CLEARED"
    else:
        outcome = "UNDER_INVESTIGATION"

    summary = state.get("reasoning", "") or f"Case {state['case_id']}: {state.get('risk_level', 'LOW')} risk, action={action}"

    stored = False
    try:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            from app.db.database import CaseMemoryRecord
            existing = await db.execute(
                select(CaseMemoryRecord).where(CaseMemoryRecord.case_id == state["case_id"])
            )
            if not existing.scalar_one_or_none():
                await store_case_memory(
                    db,
                    case_id=state["case_id"],
                    summary=summary,
                    fraud_patterns=state.get("fraud_patterns", []),
                    outcome=outcome,
                )
                stored = True
    except Exception:
        pass

    # Write case record to TigerGraph (non-fatal if unavailable)
    tg_result = {"is_mock": True}
    try:
        tg_result = await _tg_client_wf.write_case_to_graph({
            "case_id": state["case_id"],
            "customer_id": state.get("customer_id", ""),
            "risk_level": state.get("risk_level", "LOW"),
            "status": str(state.get("status", "")),
            "fraud_patterns": state.get("fraud_patterns", []),
        })
    except Exception:
        pass

    tg_note = "written to graph" if (tg_result.get("success") and not tg_result.get("is_mock")) else "graph write skipped (mock/unavailable)"
    return {
        "timeline": [_step("write_memory",
                           f"Memory {'written' if stored else 'skipped (exists)'}; {tg_note} — outcome: {outcome}",
                           {"tg_mock": tg_result.get("is_mock", True), "db_stored": stored})],
    }


def build_workflow() -> StateGraph:
    workflow = StateGraph(InvestigationState)

    workflow.add_node("create_case", create_case_node)
    workflow.add_node("graph_investigation", graph_investigation_node)
    workflow.add_node("collect_evidence", collect_evidence_node)
    workflow.add_node("retrieve_history", retrieve_history_node)
    workflow.add_node("detect_patterns", detect_patterns_node)
    workflow.add_node("assess_risk", assess_risk_node)
    workflow.add_node("assess_uncertainty", assess_uncertainty_node)
    workflow.add_node("request_additional_evidence", request_additional_evidence_node)
    workflow.add_node("recommend_action", recommend_action_node)
    workflow.add_node("check_approval", check_approval_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("explain_decision", explain_decision_node)
    workflow.add_node("update_case", update_case_node)
    workflow.add_node("write_memory", write_memory_node)

    workflow.set_entry_point("create_case")
    workflow.add_edge("create_case", "graph_investigation")
    workflow.add_edge("graph_investigation", "collect_evidence")
    workflow.add_edge("collect_evidence", "retrieve_history")
    workflow.add_edge("retrieve_history", "detect_patterns")
    workflow.add_edge("detect_patterns", "assess_risk")
    workflow.add_edge("assess_risk", "assess_uncertainty")
    workflow.add_conditional_edges(
        "assess_uncertainty",
        decide_evidence_sufficiency,
        {"request_evidence": "request_additional_evidence", "recommend_action": "recommend_action"}
    )
    # Evidence pause: workflow stops here; resumed via resume_investigation()
    workflow.add_edge("request_additional_evidence", END)
    workflow.add_edge("recommend_action", "check_approval")
    workflow.add_edge("check_approval", "execute_action")
    workflow.add_edge("execute_action", "explain_decision")
    workflow.add_edge("explain_decision", "update_case")
    workflow.add_edge("update_case", "write_memory")
    workflow.add_edge("write_memory", END)

    return workflow.compile()


_compiled_workflow = None


def get_workflow():
    global _compiled_workflow
    if _compiled_workflow is None:
        _compiled_workflow = build_workflow()
    return _compiled_workflow


def build_resume_workflow() -> StateGraph:
    """Minimal workflow that resumes after additional evidence is submitted."""
    workflow = StateGraph(InvestigationState)

    workflow.add_node("assess_uncertainty", assess_uncertainty_node)
    workflow.add_node("recommend_action", recommend_action_node)
    workflow.add_node("check_approval", check_approval_node)
    workflow.add_node("execute_action", execute_action_node)
    workflow.add_node("explain_decision", explain_decision_node)
    workflow.add_node("update_case", update_case_node)
    workflow.add_node("write_memory", write_memory_node)

    workflow.set_entry_point("assess_uncertainty")
    # After new evidence, always proceed to recommendation (no further pause)
    workflow.add_edge("assess_uncertainty", "recommend_action")
    workflow.add_edge("recommend_action", "check_approval")
    workflow.add_edge("check_approval", "execute_action")
    workflow.add_edge("execute_action", "explain_decision")
    workflow.add_edge("explain_decision", "update_case")
    workflow.add_edge("update_case", "write_memory")
    workflow.add_edge("write_memory", END)

    return workflow.compile()


_resume_workflow = None


def get_resume_workflow():
    global _resume_workflow
    if _resume_workflow is None:
        _resume_workflow = build_resume_workflow()
    return _resume_workflow


async def resume_investigation(existing_state: dict, new_evidence: list[dict]) -> dict:
    """Resume an AWAITING_EVIDENCE case after human-submitted evidence arrives."""
    # Merge new evidence, avoiding duplicates by evidence_id
    prior_evidence = existing_state.get("evidence", [])
    prior_ids = {e.get("evidence_id") for e in prior_evidence}
    merged_evidence = prior_evidence + [e for e in new_evidence if e.get("evidence_id") not in prior_ids]

    resume_state = InvestigationState(**{
        **existing_state,
        "evidence": merged_evidence,
        "additional_evidence": new_evidence,
        "needs_more_evidence": False,
        "status": CaseStatus.UNDER_REVIEW,
        "timeline": existing_state.get("timeline", []) + [
            _step("evidence_received",
                  f"Received {len(new_evidence)} new evidence item(s) — resuming assessment")
        ],
    })

    try:
        workflow = get_resume_workflow()
        final_state = await workflow.ainvoke(resume_state)
        return dict(final_state)
    except Exception as e:
        return {**resume_state, "error": str(e), "status": CaseStatus.ESCALATED}


async def run_investigation(case_id: str, customer_id: str, account_id: str, trigger: dict) -> dict:
    workflow = get_workflow()
    initial_state = InvestigationState(
        case_id=case_id,
        customer_id=customer_id,
        account_id=account_id,
        trigger=trigger,
        graph_data={},
        transactions=[],
        evidence=[],
        similar_cases=[],
        fraud_patterns=[],
        risk_score=0.0,
        risk_level="LOW",
        confidence=0.0,
        uncertainty={},
        needs_more_evidence=False,
        evidence_requests=[],
        additional_evidence=[],
        recommendation={},
        approval_status="",
        reasoning="",
        timeline=[],
        iteration_count=0,
        status=CaseStatus.NEW,
        error=""
    )
    try:
        final_state = await workflow.ainvoke(initial_state)
        return dict(final_state)
    except Exception as e:
        return {**initial_state, "error": str(e), "status": CaseStatus.ESCALATED}
