from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class CaseStatus(str, Enum):
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    UNDER_REVIEW = "UNDER_REVIEW"
    ACTION_RECOMMENDED = "ACTION_RECOMMENDED"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLEARED = "CLEARED"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FraudPattern(str, Enum):
    ACCOUNT_TAKEOVER = "ACCOUNT_TAKEOVER"
    SYNTHETIC_IDENTITY = "SYNTHETIC_IDENTITY"
    FIRST_PARTY_FRAUD = "FIRST_PARTY_FRAUD"
    CARD_NOT_PRESENT = "CARD_NOT_PRESENT"
    MONEY_LAUNDERING = "MONEY_LAUNDERING"
    VELOCITY_ABUSE = "VELOCITY_ABUSE"


class Evidence(BaseModel):
    evidence_id: str
    evidence_type: str  # supporting, contradicting, missing
    source: str
    content: str
    reliability: float = Field(ge=0.0, le=1.0)


class UncertaintyAssessment(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty_level: str  # LOW, MEDIUM, HIGH
    missing_evidence: list[str] = []
    fraud_hypotheses: list[dict] = []
    supporting_evidence: list[Evidence] = []
    contradicting_evidence: list[Evidence] = []


class Recommendation(BaseModel):
    action: str
    reason: str
    supporting_evidence: list[str] = []
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    remaining_uncertainty: str = ""
    policy_basis: str = ""
    requires_approval: bool = False
    approver_role: Optional[str] = None
    execution_status: str = "RECOMMENDED"  # RECOMMENDED, PENDING_APPROVAL, EXECUTED, REJECTED


class Case(BaseModel):
    case_id: str
    status: CaseStatus = CaseStatus.NEW
    risk_level: RiskLevel = RiskLevel.LOW
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    customer_id: str
    account_id: str
    trigger_type: str
    trigger_details: dict = {}
    fraud_patterns: list[FraudPattern] = []
    evidence: list[Evidence] = []
    uncertainty: Optional[UncertaintyAssessment] = None
    recommendation: Optional[Recommendation] = None
    investigation_timeline: list[dict] = []
    agent_reasoning: str = ""
    similar_cases: list[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class InvestigateRequest(BaseModel):
    customer_id: str
    account_id: str
    trigger_type: str
    trigger_details: dict = {}


class EvidenceSubmission(BaseModel):
    evidence_type: str
    source: str
    content: str
    reliability: float = Field(default=0.8, ge=0.0, le=1.0)


class ApprovalRequest(BaseModel):
    approved: bool
    reason: str = ""
    approver_id: str = "analyst"
