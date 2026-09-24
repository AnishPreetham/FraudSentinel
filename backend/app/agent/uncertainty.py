from typing import Any
from app.models.case import Evidence, UncertaintyAssessment

EVIDENCE_WEIGHTS = {
    "graph_connection": 0.90,
    "transaction_pattern": 0.85,
    "device_match": 0.80,
    "historical_case": 0.75,
    "ip_match": 0.70,
    "velocity": 0.80,
    "geography": 0.65,
    "biometric": 0.95,
    "kyc_status": 0.60,
    "customer_statement": 0.40,
}

REQUIRED_EVIDENCE_TYPES = {
    "ACCOUNT_TAKEOVER": ["device_match", "geography", "transaction_pattern"],
    "MONEY_LAUNDERING": ["graph_connection", "transaction_pattern", "velocity"],
    "SYNTHETIC_IDENTITY": ["kyc_status", "graph_connection", "historical_case"],
    "VELOCITY_ABUSE": ["velocity", "transaction_pattern"],
    "FIRST_PARTY_FRAUD": ["transaction_pattern", "historical_case", "kyc_status"],
    "CARD_NOT_PRESENT": ["transaction_pattern", "ip_match"],
}


def calculate_confidence(evidence_list: list[Evidence]) -> float:
    if not evidence_list:
        return 0.0

    supporting = [e for e in evidence_list if e.evidence_type == "supporting"]
    contradicting = [e for e in evidence_list if e.evidence_type == "contradicting"]

    if not supporting:
        return 0.1

    support_score = sum(
        EVIDENCE_WEIGHTS.get(e.source.lower().replace(" ", "_"), 0.6) * e.reliability
        for e in supporting
    ) / max(len(supporting), 1)

    contradict_penalty = sum(
        EVIDENCE_WEIGHTS.get(e.source.lower().replace(" ", "_"), 0.5) * e.reliability
        for e in contradicting
    ) * 0.5

    raw = support_score - (contradict_penalty / max(len(supporting), 1))
    return max(0.0, min(1.0, raw))


def identify_missing_evidence(evidence_list: list[Evidence], fraud_patterns: list[str]) -> list[str]:
    present_sources = {e.source.lower().replace(" ", "_") for e in evidence_list if e.evidence_type == "supporting"}
    missing = set()
    for pattern in fraud_patterns:
        required = REQUIRED_EVIDENCE_TYPES.get(pattern, [])
        for req in required:
            if req not in present_sources:
                missing.add(_format_missing(req))
    return sorted(missing)


def _format_missing(evidence_type: str) -> str:
    labels = {
        "device_match": "Device fingerprint verification",
        "geography": "Geolocation / IP analysis",
        "transaction_pattern": "Transaction pattern analysis",
        "graph_connection": "Connected entity graph analysis",
        "velocity": "Transaction velocity check",
        "kyc_status": "KYC / identity verification",
        "historical_case": "Historical case lookup",
        "ip_match": "IP address correlation",
        "biometric": "Biometric authentication result",
        "customer_statement": "Customer explanation or dispute",
    }
    return labels.get(evidence_type, evidence_type.replace("_", " ").title())


def build_fraud_hypotheses(evidence_list: list[Evidence], fraud_patterns: list[str]) -> list[dict]:
    hypotheses = []
    for pattern in fraud_patterns:
        supporting = [e for e in evidence_list if e.evidence_type == "supporting"]
        contradicting = [e for e in evidence_list if e.evidence_type == "contradicting"]
        support_count = len(supporting)
        contradict_count = len(contradicting)
        confidence = support_count / max(support_count + contradict_count, 1)
        hypotheses.append({
            "hypothesis": pattern,
            "confidence": round(confidence, 2),
            "supporting_count": support_count,
            "contradicting_count": contradict_count,
            "status": "LIKELY" if confidence > 0.7 else "POSSIBLE" if confidence > 0.4 else "UNLIKELY"
        })
    return hypotheses


def assess_uncertainty(evidence_list: list[Evidence], fraud_patterns: list[str]) -> UncertaintyAssessment:
    confidence = calculate_confidence(evidence_list)
    missing = identify_missing_evidence(evidence_list, fraud_patterns)
    hypotheses = build_fraud_hypotheses(evidence_list, fraud_patterns)

    if confidence >= 0.8:
        uncertainty_level = "LOW"
    elif confidence >= 0.5:
        uncertainty_level = "MEDIUM"
    else:
        uncertainty_level = "HIGH"

    supporting = [e for e in evidence_list if e.evidence_type == "supporting"]
    contradicting = [e for e in evidence_list if e.evidence_type == "contradicting"]

    return UncertaintyAssessment(
        confidence=round(confidence, 3),
        uncertainty_level=uncertainty_level,
        missing_evidence=missing,
        fraud_hypotheses=hypotheses,
        supporting_evidence=supporting,
        contradicting_evidence=contradicting
    )
