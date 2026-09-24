from typing import Any
from app.agent.policy import validate_action, PolicyDecision
from app.models.case import RiskLevel


def determine_next_action(
    risk_score: float,
    risk_level: str,
    confidence: float,
    fraud_patterns: list[str],
    evidence_list: list[dict],
    needs_more_evidence: bool,
) -> dict:
    """
    Deterministic next-best-action engine.
    Returns a dict with action, reason, policy_decision, and metadata.
    """

    if needs_more_evidence:
        return _build_action("step_up_authentication", confidence, risk_level,
                             "Insufficient evidence — requesting additional verification",
                             ["Additional evidence needed to reach confidence threshold"])

    supporting = [e for e in evidence_list if e.get("evidence_type") == "supporting"]
    contradicting = [e for e in evidence_list if e.get("evidence_type") == "contradicting"]
    has_contradicting = len(contradicting) > 0

    # Pattern-specific routing
    if "ACCOUNT_TAKEOVER" in fraud_patterns:
        if confidence >= 0.75:
            return _build_action("block_account", confidence, risk_level,
                                 "Account takeover confirmed — immediate block required",
                                 ["New device login detected", "Unusual geography", "Rapid transfers post-login"])
        elif confidence >= 0.5:
            return _build_action("escalate_to_analyst", confidence, risk_level,
                                 "Possible account takeover — analyst review required",
                                 ["Multiple risk signals present but confidence below threshold"])
        else:
            return _build_action("step_up_authentication", confidence, risk_level,
                                 "Suspicious login detected — request step-up auth",
                                 ["New device login", "Confidence insufficient for block"])

    if "MONEY_LAUNDERING" in fraud_patterns:
        if confidence >= 0.7:
            return _build_action("block_account", confidence, risk_level,
                                 "Money laundering ring detected — block all connected accounts",
                                 ["Shared device ring found", "Structured transfers below reporting threshold", "Connected accounts flagged"])
        elif confidence >= 0.5:
            return _build_action("file_sar_report", confidence, risk_level,
                                 "Suspicious transaction patterns consistent with layering",
                                 ["Multiple accounts", "Structured amounts"])

    if "VELOCITY_ABUSE" in fraud_patterns:
        if confidence >= 0.6:
            return _build_action("block_transaction", confidence, risk_level,
                                 "Velocity abuse pattern — block current transaction",
                                 ["Unusual transaction velocity", "Pattern matches velocity fraud"])
        else:
            return _build_action("monitor_account", confidence, risk_level,
                                 "Elevated velocity — enhanced monitoring",
                                 ["Transaction frequency above baseline"])

    # Risk-level fallback routing
    if risk_level in ("HIGH", "CRITICAL"):
        if confidence >= 0.75 and not has_contradicting:
            return _build_action("block_account", confidence, risk_level,
                                 "High risk with strong evidence — account block recommended",
                                 [e.get("content", "") for e in supporting[:3]])
        elif confidence >= 0.5:
            return _build_action("escalate_to_analyst", confidence, risk_level,
                                 "High risk but moderate confidence — analyst review needed",
                                 ["Risk signals present", "Further investigation required"])
        else:
            return _build_action("step_up_authentication", confidence, risk_level,
                                 "High risk profile with insufficient evidence",
                                 ["Request customer verification before action"])

    elif risk_level == "MEDIUM":
        if confidence >= 0.7:
            return _build_action("monitor_account", confidence, risk_level,
                                 "Medium risk confirmed — enhanced monitoring initiated",
                                 ["Risk signals present but not conclusive"])
        else:
            return _build_action("warn_customer", confidence, risk_level,
                                 "Medium risk — notify customer of suspicious activity",
                                 ["Precautionary notification", "Continue monitoring"])

    else:  # LOW
        return _build_action("allow_transaction", confidence, risk_level,
                             "Low risk profile — transaction permitted",
                             ["No significant risk signals detected"])


def _build_action(action: str, confidence: float, risk_level: str, reason: str, evidence: list[str]) -> dict:
    policy = validate_action(action, confidence, risk_level)
    return {
        "action": action,
        "reason": reason,
        "supporting_evidence": [e for e in evidence if e],
        "confidence": confidence,
        "policy_decision": {
            "allowed": policy.allowed,
            "requires_approval": policy.requires_approval,
            "approver_role": policy.approver_role,
            "auto_executable": policy.auto_executable,
            "policy_basis": policy.policy_basis,
        }
    }
