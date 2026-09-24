"""
LLM reasoning module — Anthropic Claude integration.

Provides evidence synthesis and case summary generation.
Deterministic policy decisions are NEVER delegated here.
Falls back to rule-based text when ANTHROPIC_API_KEY is unset or the call fails.
"""
import os
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
_MODEL = os.getenv("LLM_MODEL", "claude-haiku-4-5-20251001")
_TIMEOUT = 20  # seconds
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    if not _API_KEY:
        return None
    try:
        import anthropic
        _client = anthropic.Anthropic(api_key=_API_KEY, timeout=_TIMEOUT)
        return _client
    except Exception as e:
        logger.warning(f"Anthropic client init failed: {e}")
        return None


def llm_available() -> bool:
    return bool(_API_KEY) and _get_client() is not None


def _call_llm(system: str, user: str, max_tokens: int = 512) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text if response.content else None
    except Exception as e:
        logger.warning(f"LLM call failed: {e}")
        return None


def synthesize_case_summary(
    case_id: str,
    customer_id: str,
    risk_level: str,
    risk_score: float,
    confidence: float,
    fraud_patterns: list[str],
    supporting_evidence: list[dict],
    contradicting_evidence: list[dict],
    missing_evidence: list[str],
    similar_cases: list[dict],
    recommendation_action: str,
    recommendation_reason: str,
    requires_approval: bool,
    approver_role: Optional[str],
) -> dict:
    """
    Use LLM to generate a concise, auditable investigation summary.
    Returns {'summary': str, 'llm_used': bool}.
    Evidence is passed as structured data; the LLM must not invent new facts.
    """
    # Build structured evidence packet — treated as DATA, not instructions
    evidence_packet = {
        "case_id": case_id,
        "customer_id": customer_id,
        "risk_level": risk_level,
        "risk_score": round(risk_score, 2),
        "confidence": round(confidence, 2),
        "fraud_patterns": fraud_patterns,
        "supporting_evidence": [
            {"source": e.get("source"), "content": e.get("content"), "reliability": e.get("reliability")}
            for e in supporting_evidence[:6]
        ],
        "contradicting_evidence": [
            {"source": e.get("source"), "content": e.get("content")}
            for e in contradicting_evidence[:3]
        ],
        "missing_evidence": missing_evidence[:4],
        "similar_cases": [
            {"case_id": c.get("case_id"), "similarity": c.get("similarity"), "outcome": c.get("outcome")}
            for c in similar_cases[:3]
        ],
        "recommended_action": recommendation_action,
        "recommendation_reason": recommendation_reason,
        "requires_approval": requires_approval,
        "approver_role": approver_role,
    }

    system_prompt = (
        "You are a fraud investigation analyst assistant. "
        "You receive a structured evidence packet and produce a concise, factual case summary. "
        "Rules:\n"
        "1. Only use facts from the evidence packet — do not invent entities, amounts, or patterns.\n"
        "2. Be concise: 3–5 sentences.\n"
        "3. State what was found, what pattern was detected, what action is recommended, and why.\n"
        "4. If evidence is contradicting or missing, acknowledge the uncertainty.\n"
        "5. Do not include personal opinions, speculation, or chain-of-thought.\n"
        "6. Do not override or question the recommended action or approval requirement.\n"
        "Output only the plain-text summary paragraph."
    )

    user_prompt = (
        "Produce a concise fraud investigation summary based on this evidence packet. "
        "Stick strictly to the facts in the packet.\n\n"
        f"EVIDENCE PACKET:\n{json.dumps(evidence_packet, indent=2)}"
    )

    llm_text = _call_llm(system_prompt, user_prompt, max_tokens=300)

    if llm_text:
        logger.info(f"LLM summary generated for case {case_id} using {_MODEL}")
        return {"summary": llm_text.strip(), "llm_used": True, "model": _MODEL}

    # Deterministic fallback
    fallback = _deterministic_summary(
        case_id, customer_id, risk_level, confidence, fraud_patterns,
        supporting_evidence, missing_evidence, recommendation_action,
        recommendation_reason, requires_approval, approver_role
    )
    return {"summary": fallback, "llm_used": False, "model": "deterministic_fallback"}


def _deterministic_summary(
    case_id, customer_id, risk_level, confidence, fraud_patterns,
    supporting_evidence, missing_evidence, recommendation_action,
    recommendation_reason, requires_approval, approver_role
) -> str:
    parts = [
        f"Investigation {case_id} for customer {customer_id} assessed as {risk_level} risk "
        f"(confidence {confidence:.0%})."
    ]
    if fraud_patterns:
        parts.append(f"Detected pattern(s): {', '.join(fraud_patterns)}.")
    if supporting_evidence:
        top = supporting_evidence[0]
        parts.append(f"Key evidence: {top.get('content', '')} (source: {top.get('source', 'unknown')}).")
    if missing_evidence:
        parts.append(f"Unresolved: {'; '.join(missing_evidence[:2])}.")
    approval_note = f"Requires {approver_role} approval." if requires_approval else "Auto-authorized."
    parts.append(f"Recommended action: {recommendation_action} — {recommendation_reason}. {approval_note}")
    return " ".join(parts)
