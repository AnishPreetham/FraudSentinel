# FraudSentinel — Agent Workflow Reference

## State Machine Overview

The investigation runs as a LangGraph `StateGraph` with typed state (`InvestigationState`). All nodes receive the full state dict and return partial updates — LangGraph merges them.

## Primary Workflow (14 nodes)

```
receive_case
    │
    ▼
retrieve_history         ← queries SQLite case memory; falls back to TigerGraph
    │
    ▼
collect_evidence         ← gathers transaction data, device fingerprints, KYC
    │
    ▼
detect_patterns          ← identifies MONEY_LAUNDERING, ACCOUNT_TAKEOVER, VELOCITY_ABUSE, etc.
    │
    ▼
assess_uncertainty       ← computes confidence score (0.0–1.0) and missing evidence list
    │
    ▼
[conditional: enough_evidence?]
    │                              │
    ▼ YES                          ▼ NO
recommend_action          request_additional_evidence
    │                              │
    ▼                              ▼
check_approval           ──────► END (status=AWAITING_EVIDENCE)
    │
    ▼
execute_action           ← auto-executes or marks PENDING_APPROVAL
    │
    ▼
explain_decision         ← Anthropic LLM or deterministic summary
    │
    ▼
update_case              ← writes final status to DB
    │
    ▼
write_memory             ← stores to SQLite case memory + TigerGraph graph write
    │
    ▼
END
```

## Resume Workflow (7 nodes)

When a case is in `AWAITING_EVIDENCE` and the client POSTs new evidence:

```
assess_uncertainty → recommend_action → check_approval → execute_action
    → explain_decision → update_case → write_memory → END
```

Evidence items are deduplicated by `evidence_id` before resuming.

## Node Reference

### `receive_case`
- **Input:** `case_id`, `customer_id`, `account_id`, `trigger`
- **Output:** Initializes all state fields; sets `status = UNDER_INVESTIGATION`

### `retrieve_history`
- **Input:** `customer_id`
- **Output:** `similar_cases` list from SQLite case memory (Jaccard similarity on fraud patterns)
- **Fallback:** Returns empty list if memory is empty (never errors)

### `collect_evidence`
- **Input:** `customer_id`, `account_id`, `trigger`
- **Output:** `evidence` list, each item: `{evidence_id, evidence_type, source, content, reliability, timestamp}`
- **Note:** Uses TigerGraph mock data when credentials absent; items are labeled `source: "mock_tigergraph"`

### `detect_patterns`
- **Input:** `evidence`
- **Output:** `fraud_patterns` list (e.g., `["MONEY_LAUNDERING", "VELOCITY_ABUSE"]`), `risk_score`, `risk_level` (LOW/MEDIUM/HIGH/CRITICAL)

### `assess_uncertainty`
- **Input:** `evidence`, `fraud_patterns`
- **Output:** `confidence` (0.0–1.0), `missing_evidence` list, `uncertainty_level` (LOW/MEDIUM/HIGH)
- **Algorithm:** Weighted sum of evidence reliability, penalized by contradictions, capped at 1.0

### `recommend_action`
- **Input:** `risk_level`, `risk_score`, `confidence`, `fraud_patterns`, `similar_cases`
- **Output:** `recommendation` dict with `action`, `reason`, `requires_approval`, `approver_role`, `policy_basis`
- **Actions:** `block_account`, `monitor_account`, `allow_transaction`, `step_up_authentication`, `file_sar`, `needs_more_evidence`

### `check_approval`
- **Input:** `recommendation`
- **Output:** `status` — `PENDING_APPROVAL` if `requires_approval=True`, else unchanged

### `execute_action`
- **Input:** `recommendation`, `status`
- **Output:** `recommendation.execution_status` — `AUTO_EXECUTED` or `PENDING_APPROVAL`
- **Safety:** Never executes against real systems; marks DB state only

### `explain_decision`
- **Input:** full state
- **Output:** `reasoning` (natural language), timeline step with `llm_used: true/false`
- **LLM call:** Sends structured evidence packet to Anthropic Claude; falls back to deterministic summary if key missing or call fails

### `update_case`
- **Input:** final state
- **Output:** Writes case record to SQLite with all fields

### `write_memory`
- **Input:** `case_id`, `fraud_patterns`, `recommendation`
- **Output:** Inserts row into `case_memory` table (skips if `case_id` already present); calls `write_case_to_graph()`
- **Graph write:** Upserts `Case` vertex and `INVOLVED_IN` edge in TigerGraph; no-ops gracefully when not configured

### `request_additional_evidence`
- **Input:** `missing_evidence`
- **Output:** `status = AWAITING_EVIDENCE`, timeline step added
- **Routing:** → `END` (does NOT continue to recommend_action)

## State Schema

```python
class InvestigationState(TypedDict):
    case_id: str
    customer_id: str
    account_id: str
    trigger: dict
    status: CaseStatus          # UNDER_INVESTIGATION | AWAITING_EVIDENCE | PENDING_APPROVAL | CLOSED
    risk_level: str             # LOW | MEDIUM | HIGH | CRITICAL
    risk_score: float           # 0.0–1.0
    confidence: float           # 0.0–1.0
    fraud_patterns: list[str]
    evidence: list[dict]
    missing_evidence: list[str]
    similar_cases: list[dict]
    recommendation: dict
    reasoning: str
    timeline: list[dict]        # ordered list of {step, description, timestamp}
    error: str | None
```

## Policy Engine Rules (Deterministic)

The policy engine (`policy.py`) never delegates to LLM. Rules (evaluated in order):

1. `CRITICAL` risk → `block_account` (requires FRAUD_MANAGER approval)
2. `HIGH` risk + MONEY_LAUNDERING → `file_sar` + `block_account` (requires COMPLIANCE_OFFICER)
3. `HIGH` risk + ACCOUNT_TAKEOVER → `block_account` (requires FRAUD_ANALYST)
4. `HIGH` risk + confidence < 0.6 → `step_up_authentication` (auto-execute)
5. `MEDIUM` risk → `monitor_account` (auto-execute)
6. `LOW` risk → `allow_transaction` (auto-execute)
7. Confidence < 0.4 → `needs_more_evidence` (triggers evidence pause)
