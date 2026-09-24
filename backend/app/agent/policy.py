from dataclasses import dataclass
from typing import Optional


POLICY_RULES = {
    "block_account": {
        "requires_approval": True,
        "approver": "FRAUD_ANALYST",
        "min_confidence": 0.7,
        "auto_execute_above": None,
        "description": "Immediately suspend account access"
    },
    "block_transaction": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.6,
        "auto_execute_above": 0.9,
        "description": "Decline the specific transaction"
    },
    "monitor_account": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.4,
        "auto_execute_above": 0.5,
        "description": "Enable enhanced monitoring on account"
    },
    "file_sar_report": {
        "requires_approval": True,
        "approver": "COMPLIANCE_OFFICER",
        "min_confidence": 0.75,
        "auto_execute_above": None,
        "description": "File Suspicious Activity Report with regulators"
    },
    "allow_transaction": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.0,
        "auto_execute_above": 0.0,
        "description": "Approve the transaction"
    },
    "escalate_to_analyst": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.0,
        "auto_execute_above": 0.0,
        "description": "Route to human fraud analyst for review"
    },
    "warn_customer": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.5,
        "auto_execute_above": 0.6,
        "description": "Send fraud warning notification to customer"
    },
    "step_up_authentication": {
        "requires_approval": False,
        "approver": None,
        "min_confidence": 0.3,
        "auto_execute_above": 0.3,
        "description": "Request additional authentication from customer"
    },
    "freeze_and_investigate": {
        "requires_approval": True,
        "approver": "SENIOR_ANALYST",
        "min_confidence": 0.8,
        "auto_execute_above": None,
        "description": "Freeze account and open formal investigation"
    },
}


@dataclass
class PolicyDecision:
    action: str
    allowed: bool
    requires_approval: bool
    approver_role: Optional[str]
    auto_executable: bool
    reason: str
    policy_basis: str


def validate_action(action: str, confidence: float, risk_level: str) -> PolicyDecision:
    rule = POLICY_RULES.get(action)
    if not rule:
        return PolicyDecision(
            action=action,
            allowed=False,
            requires_approval=True,
            approver_role="COMPLIANCE_OFFICER",
            auto_executable=False,
            reason="Unknown action — requires compliance review",
            policy_basis="Default deny for unknown actions"
        )

    min_conf = rule.get("min_confidence", 0.0)
    if confidence < min_conf:
        return PolicyDecision(
            action=action,
            allowed=False,
            requires_approval=True,
            approver_role="FRAUD_ANALYST",
            auto_executable=False,
            reason=f"Confidence {confidence:.0%} below required {min_conf:.0%} for {action}",
            policy_basis=f"Policy: {action} requires minimum {min_conf:.0%} confidence"
        )

    auto_threshold = rule.get("auto_execute_above")
    auto_exec = (auto_threshold is not None) and (confidence >= auto_threshold) and (not rule["requires_approval"])
    req_approval = rule["requires_approval"] and not auto_exec

    reason_parts = []
    if auto_exec:
        reason_parts.append(f"Auto-authorized: confidence {confidence:.0%} exceeds threshold {auto_threshold:.0%}")
    elif req_approval:
        reason_parts.append(f"Requires {rule['approver']} approval for account action")
    else:
        reason_parts.append(f"Action permitted at confidence {confidence:.0%}")

    if risk_level == "CRITICAL" and not rule["requires_approval"]:
        req_approval = True
        reason_parts.append("CRITICAL risk level triggers mandatory approval override")

    return PolicyDecision(
        action=action,
        allowed=True,
        requires_approval=req_approval,
        approver_role=rule.get("approver"),
        auto_executable=auto_exec,
        reason=" | ".join(reason_parts),
        policy_basis=f"Policy Rule: {rule['description']}"
    )


def get_required_approver(action: str) -> Optional[str]:
    rule = POLICY_RULES.get(action, {})
    return rule.get("approver")


def is_auto_executable(action: str, confidence: float) -> bool:
    rule = POLICY_RULES.get(action, {})
    if rule.get("requires_approval"):
        return False
    threshold = rule.get("auto_execute_above")
    return threshold is not None and confidence >= threshold
