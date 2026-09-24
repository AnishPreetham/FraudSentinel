import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db, CaseRecord, InvestigationEvent
from app.models.case import InvestigateRequest, EvidenceSubmission, ApprovalRequest, Case, CaseStatus
from app.agent.workflow import run_investigation, resume_investigation
from app.api.demo import get_scenario, list_scenarios

router = APIRouter()

# In-memory store for active investigations (demo mode)
_active_cases: dict[str, dict] = {}


async def _run_and_store(case_id: str, customer_id: str, account_id: str, trigger: dict, db_url: str):
    """Background task to run investigation and persist result."""
    result = await run_investigation(case_id, customer_id, account_id, trigger)
    _active_cases[case_id] = result


@router.post("/investigate")
async def start_investigation(
    req: InvestigateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    case_id = f"CASE-{str(uuid.uuid4())[:8].upper()}"

    # Persist stub record
    record = CaseRecord(
        id=case_id,
        status=CaseStatus.INVESTIGATING,
        customer_id=req.customer_id,
        account_id=req.account_id,
        trigger_type=req.trigger_type,
        trigger_details=json.dumps(req.trigger_details),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()

    # Run investigation synchronously for demo reliability
    result = await run_investigation(case_id, req.customer_id, req.account_id, req.trigger_details)
    _active_cases[case_id] = result

    # Update record
    await _update_db_record(db, case_id, result)

    return {
        "case_id": case_id,
        "status": result.get("status", CaseStatus.INVESTIGATING),
        "message": "Investigation complete"
    }


@router.get("/{case_id}")
async def get_case(case_id: str, db: AsyncSession = Depends(get_db)):
    # Try in-memory first
    if case_id in _active_cases:
        return _format_case(case_id, _active_cases[case_id])

    # Try DB
    result = await db.execute(select(CaseRecord).where(CaseRecord.id == case_id))
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return _format_case_from_db(record)


@router.get("")
async def list_cases(db: AsyncSession = Depends(get_db), limit: int = 50, offset: int = 0):
    # Return in-memory cases + DB cases
    cases = []
    for case_id, state in list(_active_cases.items())[offset:offset+limit]:
        cases.append(_format_case_summary(case_id, state))

    if not cases:
        result = await db.execute(select(CaseRecord).limit(limit).offset(offset))
        for record in result.scalars().all():
            if record.id not in _active_cases:
                cases.append(_format_case_from_db(record))

    return {"cases": cases, "total": len(cases), "limit": limit, "offset": offset}


@router.post("/{case_id}/evidence")
async def submit_evidence(case_id: str, submission: EvidenceSubmission, db: AsyncSession = Depends(get_db)):
    if case_id not in _active_cases:
        raise HTTPException(status_code=404, detail="Case not found")

    state = _active_cases[case_id]
    new_evidence = {
        "evidence_id": str(uuid.uuid4()),
        "evidence_type": submission.evidence_type,
        "source": submission.source,
        "content": submission.content,
        "reliability": submission.reliability,
    }

    was_awaiting = state.get("status") == CaseStatus.AWAITING_EVIDENCE

    if was_awaiting:
        # Genuine resume: continue the paused workflow with new evidence
        updated = await resume_investigation(state, [new_evidence])
        _active_cases[case_id] = updated
        await _update_db_record(db, case_id, updated)
        return {
            "case_id": case_id,
            "status": updated.get("status"),
            "evidence_id": new_evidence["evidence_id"],
            "reassessment": "complete",
            "risk_level": updated.get("risk_level"),
            "recommended_action": updated.get("recommendation", {}).get("action"),
        }
    else:
        # Case not paused — just append evidence and update
        state["evidence"] = state.get("evidence", []) + [new_evidence]
        state["status"] = CaseStatus.UNDER_REVIEW
        _active_cases[case_id] = state
        await _update_db_record(db, case_id, state)
        return {"case_id": case_id, "status": "evidence_received", "evidence_id": new_evidence["evidence_id"]}


@router.post("/{case_id}/approve")
async def approve_action(case_id: str, approval: ApprovalRequest, db: AsyncSession = Depends(get_db)):
    if case_id not in _active_cases:
        raise HTTPException(status_code=404, detail="Case not found")

    state = _active_cases[case_id]
    rec = state.get("recommendation", {})

    if approval.approved:
        rec["execution_status"] = "EXECUTED"
        state["status"] = CaseStatus.ACTION_EXECUTED
        state["timeline"] = state.get("timeline", []) + [{
            "step": "approval_received",
            "description": f"Action approved by {approval.approver_id}: {rec.get('action', '')} executed",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"approved": True, "approver": approval.approver_id}
        }]
    else:
        rec["execution_status"] = "REJECTED"
        state["status"] = CaseStatus.ESCALATED
        state["timeline"] = state.get("timeline", []) + [{
            "step": "approval_rejected",
            "description": f"Action rejected by {approval.approver_id}: {approval.reason}",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"approved": False, "reason": approval.reason}
        }]

    state["recommendation"] = rec
    _active_cases[case_id] = state
    await _update_db_record(db, case_id, state)

    return {"case_id": case_id, "status": state["status"], "action": rec.get("action"), "execution_status": rec.get("execution_status")}


@router.get("/{case_id}/timeline")
async def get_timeline(case_id: str):
    if case_id not in _active_cases:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case_id": case_id, "timeline": _active_cases[case_id].get("timeline", [])}


async def _update_db_record(db: AsyncSession, case_id: str, state: dict):
    try:
        result = await db.execute(select(CaseRecord).where(CaseRecord.id == case_id))
        record = result.scalar_one_or_none()
        if record:
            record.status = state.get("status", CaseStatus.INVESTIGATING)
            record.risk_score = state.get("risk_score", 0.0)
            record.risk_level = state.get("risk_level", "LOW")
            record.fraud_patterns = json.dumps(state.get("fraud_patterns", []))
            record.evidence = json.dumps(state.get("evidence", []))
            record.uncertainty = json.dumps(state.get("uncertainty", {}))
            record.recommendation = json.dumps(state.get("recommendation", {}))
            record.investigation_timeline = json.dumps(state.get("timeline", []))
            record.agent_reasoning = state.get("reasoning", "")
            record.similar_cases = json.dumps(state.get("similar_cases", []))
            record.updated_at = datetime.utcnow()
            await db.commit()
    except Exception:
        pass


def _format_case(case_id: str, state: dict) -> dict:
    return {
        "case_id": case_id,
        "status": state.get("status", CaseStatus.INVESTIGATING),
        "risk_level": state.get("risk_level", "LOW"),
        "risk_score": state.get("risk_score", 0.0),
        "confidence": state.get("confidence", 0.0),
        "customer_id": state.get("customer_id", ""),
        "account_id": state.get("account_id", ""),
        "trigger": state.get("trigger", {}),
        "fraud_patterns": state.get("fraud_patterns", []),
        "evidence": state.get("evidence", []),
        "uncertainty": state.get("uncertainty", {}),
        "recommendation": state.get("recommendation", {}),
        "similar_cases": state.get("similar_cases", []),
        "investigation_timeline": state.get("timeline", []),
        "agent_reasoning": state.get("reasoning", ""),
        "graph_data": state.get("graph_data", {}),
        "error": state.get("error", ""),
    }


def _format_case_summary(case_id: str, state: dict) -> dict:
    return {
        "case_id": case_id,
        "status": state.get("status", CaseStatus.INVESTIGATING),
        "risk_level": state.get("risk_level", "LOW"),
        "risk_score": state.get("risk_score", 0.0),
        "customer_id": state.get("customer_id", ""),
        "fraud_patterns": state.get("fraud_patterns", []),
        "recommendation_action": state.get("recommendation", {}).get("action", ""),
    }


def _format_case_from_db(record: CaseRecord) -> dict:
    return {
        "case_id": record.id,
        "status": record.status,
        "risk_level": record.risk_level,
        "risk_score": record.risk_score,
        "customer_id": record.customer_id,
        "account_id": record.account_id,
        "trigger_type": record.trigger_type,
        "fraud_patterns": json.loads(record.fraud_patterns or "[]"),
        "evidence": json.loads(record.evidence or "[]"),
        "uncertainty": json.loads(record.uncertainty or "{}"),
        "recommendation": json.loads(record.recommendation or "{}"),
        "investigation_timeline": json.loads(record.investigation_timeline or "[]"),
        "agent_reasoning": record.agent_reasoning or "",
        "similar_cases": json.loads(record.similar_cases or "[]"),
    }
