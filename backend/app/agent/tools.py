import time
import uuid
from datetime import datetime
from app.graph.tigergraph import TigerGraphClient
from app.agent.uncertainty import assess_uncertainty
from app.agent.actions import determine_next_action
from app.models.case import Evidence, RiskLevel

_tg_client = TigerGraphClient()


def _wrap(tool_name: str, result: dict, start: float) -> dict:
    return {
        "tool_name": tool_name,
        "result": result,
        "is_mock": result.get("is_mock", True),
        "latency_ms": round((time.time() - start) * 1000),
        "timestamp": datetime.utcnow().isoformat(),
    }


async def investigate_customer(customer_id: str) -> dict:
    start = time.time()
    neighborhood = await _tg_client.get_customer_neighborhood(customer_id)
    connected = await _tg_client.find_connected_entities(customer_id)
    devices = await _tg_client.find_shared_devices(customer_id)

    risk_signals = neighborhood.get("profile", {}).get("risk_signals", [])
    connected_accounts = neighborhood.get("connected_accounts", [])
    shared_devices = devices.get("shared_devices", [])

    suspicious_connections = [a for a in connected_accounts if a.get("suspicious")]

    return _wrap("investigate_customer", {
        "customer_id": customer_id,
        "profile": neighborhood.get("profile", {}),
        "connected_accounts": connected_accounts,
        "shared_devices": shared_devices,
        "entities": connected.get("entities", {}),
        "risk_signals": risk_signals,
        "suspicious_connections": suspicious_connections,
        "high_risk": len(suspicious_connections) >= 2 or len(shared_devices) > 0,
        "is_mock": neighborhood.get("is_mock", True),
    }, start)


async def get_transaction_history(account_id: str, days: int = 30) -> dict:
    start = time.time()
    data = await _tg_client.get_transaction_history(account_id, days)
    transactions = data.get("transactions", [])

    total_amount = sum(t.get("amount", 0) for t in transactions)
    avg_amount = total_amount / max(len(transactions), 1)
    max_amount = max((t.get("amount", 0) for t in transactions), default=0)

    velocity_flag = len(transactions) > 5 and (
        all(t.get("amount", 0) < 5000 for t in transactions)
    )

    return _wrap("get_transaction_history", {
        "account_id": account_id,
        "transactions": transactions,
        "count": len(transactions),
        "total_amount": total_amount,
        "avg_amount": round(avg_amount, 2),
        "max_amount": max_amount,
        "velocity_flag": velocity_flag,
        "structured_amounts": velocity_flag,
        "is_mock": data.get("is_mock", True),
    }, start)


async def find_connected_entities(customer_id: str) -> dict:
    start = time.time()
    data = await _tg_client.find_connected_entities(customer_id)
    entities = data.get("entities", {})

    shared_devices = entities.get("shared_devices", [])
    shared_ips = entities.get("shared_ips", [])
    linked = entities.get("linked_accounts", [])

    suspicious_device = any(d.get("suspicious") for d in shared_devices)
    suspicious_ip = any(i.get("suspicious") for i in shared_ips)

    return _wrap("find_connected_entities", {
        "customer_id": customer_id,
        "shared_devices": shared_devices,
        "shared_ips": shared_ips,
        "linked_accounts": linked,
        "suspicious_device_sharing": suspicious_device,
        "suspicious_ip": suspicious_ip,
        "ring_detected": len(linked) >= 3 and suspicious_device,
        "is_mock": data.get("is_mock", True),
    }, start)


async def detect_fraud_patterns(transaction_data: dict, graph_data: dict) -> dict:
    start = time.time()
    patterns = []

    transactions = transaction_data.get("transactions", [])
    shared_devices = graph_data.get("shared_devices", [])
    risk_signals = graph_data.get("risk_signals", []) + transaction_data.get("risk_signals", [])

    # Money laundering: connected ring + structured amounts
    if graph_data.get("ring_detected") and transaction_data.get("structured_amounts"):
        patterns.append("MONEY_LAUNDERING")

    # Account takeover: new device + geography + transfers
    if ("new_device_login" in risk_signals or "geography_mismatch" in risk_signals):
        patterns.append("ACCOUNT_TAKEOVER")

    # Velocity abuse
    if transaction_data.get("velocity_flag") or "rapid_velocity" in risk_signals:
        patterns.append("VELOCITY_ABUSE")

    # Card not present
    cnp_merchants = ["online", "e-commerce", "digital", "virtual"]
    if any(any(m in t.get("merchant", "").lower() for m in cnp_merchants) for t in transactions):
        patterns.append("CARD_NOT_PRESENT")

    return _wrap("detect_fraud_patterns", {
        "patterns_detected": patterns,
        "pattern_count": len(patterns),
        "high_confidence_patterns": patterns[:2] if len(patterns) >= 2 else patterns,
        "is_mock": True,
    }, start)


async def retrieve_similar_cases(case_features: dict) -> dict:
    start = time.time()
    data = await _tg_client.find_similar_cases(case_features)
    return _wrap("retrieve_similar_cases", {
        "similar_cases": data.get("similar_cases", []),
        "count": len(data.get("similar_cases", [])),
        "is_mock": data.get("is_mock", True),
    }, start)


async def assess_risk(evidence_list: list[dict], patterns: list[str], graph_data: dict) -> dict:
    start = time.time()
    evidence_objects = [
        Evidence(
            evidence_id=e.get("evidence_id", str(uuid.uuid4())),
            evidence_type=e.get("evidence_type", "supporting"),
            source=e.get("source", "unknown"),
            content=e.get("content", ""),
            reliability=e.get("reliability", 0.7)
        )
        for e in evidence_list
    ]

    uncertainty = assess_uncertainty(evidence_objects, patterns)
    supporting_count = len(uncertainty.supporting_evidence)
    contradicting_count = len(uncertainty.contradicting_evidence)

    base_score = uncertainty.confidence
    pattern_boost = min(len(patterns) * 0.1, 0.3)
    risk_score = min(base_score + pattern_boost, 1.0)

    if risk_score >= 0.85:
        risk_level = "CRITICAL"
    elif risk_score >= 0.65:
        risk_level = "HIGH"
    elif risk_score >= 0.40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return _wrap("assess_risk", {
        "risk_score": round(risk_score, 3),
        "risk_level": risk_level,
        "confidence": uncertainty.confidence,
        "uncertainty_level": uncertainty.uncertainty_level,
        "supporting_evidence_count": supporting_count,
        "contradicting_evidence_count": contradicting_count,
        "missing_evidence": uncertainty.missing_evidence,
        "fraud_hypotheses": uncertainty.fraud_hypotheses,
        "is_mock": True,
    }, start)


async def request_additional_evidence(case_id: str, evidence_type: str, reason: str) -> dict:
    start = time.time()
    request_id = str(uuid.uuid4())[:8]
    return _wrap("request_additional_evidence", {
        "case_id": case_id,
        "request_id": request_id,
        "evidence_type": evidence_type,
        "reason": reason,
        "status": "REQUESTED",
        "instructions": f"Please provide {evidence_type} for case {case_id}: {reason}",
        "is_mock": True,
    }, start)


async def recommend_action(case_id: str, assessment: dict) -> dict:
    start = time.time()
    action_result = determine_next_action(
        risk_score=assessment.get("risk_score", 0),
        risk_level=assessment.get("risk_level", "LOW"),
        confidence=assessment.get("confidence", 0),
        fraud_patterns=assessment.get("fraud_patterns", []),
        evidence_list=assessment.get("evidence", []),
        needs_more_evidence=assessment.get("needs_more_evidence", False),
    )
    return _wrap("recommend_action", {
        "case_id": case_id,
        **action_result,
        "is_mock": True,
    }, start)
