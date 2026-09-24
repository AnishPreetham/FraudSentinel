export type CaseStatus =
  | 'NEW' | 'INVESTIGATING' | 'AWAITING_EVIDENCE' | 'UNDER_REVIEW'
  | 'ACTION_RECOMMENDED' | 'PENDING_APPROVAL' | 'ACTION_EXECUTED'
  | 'ESCALATED' | 'RESOLVED' | 'CLEARED'

export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type FraudPattern =
  | 'ACCOUNT_TAKEOVER' | 'SYNTHETIC_IDENTITY' | 'FIRST_PARTY_FRAUD'
  | 'CARD_NOT_PRESENT' | 'MONEY_LAUNDERING' | 'VELOCITY_ABUSE'

export interface Evidence {
  evidence_id: string
  evidence_type: 'supporting' | 'contradicting' | 'missing'
  source: string
  content: string
  reliability: number
}

export interface UncertaintyAssessment {
  confidence: number
  uncertainty_level: 'LOW' | 'MEDIUM' | 'HIGH'
  missing_evidence: string[]
  fraud_hypotheses: Array<{
    hypothesis: string
    confidence: number
    status: string
  }>
  supporting_evidence: Evidence[]
  contradicting_evidence: Evidence[]
}

export interface Recommendation {
  action: string
  reason: string
  supporting_evidence: string[]
  risk_level: RiskLevel
  confidence: number
  remaining_uncertainty: string
  policy_basis: string
  requires_approval: boolean
  approver_role?: string
  execution_status: string
}

export interface TimelineStep {
  step: string
  description: string
  timestamp: string
  data?: Record<string, unknown>
}

export interface Case {
  case_id: string
  status: CaseStatus
  risk_level: RiskLevel
  risk_score: number
  confidence: number
  customer_id: string
  account_id: string
  trigger: Record<string, unknown>
  fraud_patterns: FraudPattern[]
  evidence: Evidence[]
  uncertainty: UncertaintyAssessment
  recommendation: Recommendation
  similar_cases: Array<{
    case_id: string
    similarity: number
    outcome: string
    pattern: string
    description: string
  }>
  investigation_timeline: TimelineStep[]
  agent_reasoning: string
  graph_data: Record<string, unknown>
  error?: string
}

export interface GraphNode {
  id: string
  type: 'customer' | 'account' | 'transaction' | 'device' | 'ip' | 'merchant'
  label: string
  suspicious?: boolean
}

export interface GraphLink {
  source: string
  target: string
  suspicious?: boolean
  weight?: number
}
