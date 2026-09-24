# FraudSentinel — System Architecture

## Design Principles

1. **Deterministic policy, not LLM decisions** — Risk decisions and action selection are always rule-based. LLM generates summaries only.
2. **Genuine human-in-the-loop** — Evidence pause is a real workflow halt, not a simulated delay.
3. **Honest integration labeling** — Every integration reports its actual mode: real / mock / deterministic_fallback.
4. **No silent fallbacks** — If TigerGraph or LLM calls fail, the timeline step says so explicitly.
5. **Testable without credentials** — Full test suite runs with SQLite in-memory; zero external dependencies required.

## Component Map

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React + TypeScript + Vite + Tailwind                        │
│                                                              │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────────┐ │
│  │ Investigation│  │ Evidence      │  │ Network Graph Viz  │ │
│  │ Dashboard    │  │ Submission    │  │ (D3.js)            │ │
│  └──────────────┘  └───────────────┘  └───────────────────┘ │
└────────────────────────────┬─────────────────────────────────┘
                             │ HTTP/JSON
┌────────────────────────────▼─────────────────────────────────┐
│                    FASTAPI BACKEND                            │
│                                                              │
│  Routers:                                                    │
│  POST /api/demo/scenario/{name}  → run pre-built scenario    │
│  GET  /api/cases                 → list cases                │
│  GET  /api/cases/{id}            → case detail               │
│  POST /api/cases/{id}/approve    → human approval            │
│  POST /api/cases/{id}/evidence   → submit additional evidence│
│  GET  /health                    → liveness                  │
│  GET  /ready                     → readiness + integrations  │
└──────┬─────────────────────────────────────┬─────────────────┘
       │                                     │
┌──────▼──────────────┐             ┌────────▼───────────────┐
│   LANGGRAPH AGENT   │             │   SQLAlchemy + aiosqlite│
│                     │             │                        │
│  workflow.py        │             │  Tables:               │
│  • Primary workflow │             │  • cases               │
│    (14 nodes)       │             │  • evidence            │
│  • Resume workflow  │             │  • investigation_steps │
│    (7 nodes)        │             │  • case_memory         │
│                     │             └────────────────────────┘
│  Modules:           │
│  • evidence.py      │             ┌────────────────────────┐
│  • patterns.py      │             │  TIGERGRAPH (optional) │
│  • uncertainty.py   ├────────────►│                        │
│  • policy.py        │             │  REST++ API (Basic Auth)│
│  • actions.py       │             │  • GetCustomerHistory  │
│  • llm.py           │             │  • DetectFraudRings    │
│  • case_memory.py   │             │  • GetRelatedTxns      │
└─────────────────────┘             │  • vertex/edge upserts │
                                    │                        │
                                    │  Mock mode when        │
                                    │  credentials absent    │
                                    └────────────────────────┘
                    ┌────────────────────────┐
                    │  ANTHROPIC CLAUDE API  │
                    │  (optional)            │
                    │                        │
                    │  claude-haiku-4-5      │
                    │  Generates case        │
                    │  summaries from        │
                    │  structured evidence   │
                    │  packet               │
                    │                        │
                    │  Deterministic         │
                    │  fallback when key     │
                    │  not configured        │
                    └────────────────────────┘
```

## Data Flow — Normal Investigation

```
1. Client POSTs trigger event
2. FastAPI creates case record in SQLite
3. run_investigation() invokes primary LangGraph workflow
4. retrieve_history: queries case_memory for similar past cases (Jaccard similarity)
5. collect_evidence: calls TigerGraph (or mock) for transaction data, device, KYC
6. detect_patterns: rule-based pattern matching → fraud_patterns, risk_score, risk_level
7. assess_uncertainty: confidence score from evidence reliability + contradiction penalty
8. If confidence < threshold → request_additional_evidence → END (AWAITING_EVIDENCE)
9. Else → recommend_action: deterministic policy lookup → action + approval requirement
10. execute_action: sets execution_status = AUTO_EXECUTED or PENDING_APPROVAL
11. explain_decision: Anthropic LLM call (or deterministic fallback) → case summary
12. update_case: final DB write
13. write_memory: store_case_memory() + write_case_to_graph()
14. FastAPI returns full investigation result to client
```

## Data Flow — Evidence Pause/Resume

```
1. Primary workflow ends at AWAITING_EVIDENCE (step 8 above)
2. FastAPI returns status=AWAITING_EVIDENCE to client
3. Analyst reviews case, submits evidence: POST /api/cases/{id}/evidence
4. cases.py detects was_awaiting=True, calls resume_investigation(state, [new_evidence])
5. resume_investigation() deduplicates evidence by evidence_id
6. Invokes 7-node resume workflow: assess_uncertainty → ... → write_memory → END
7. Returns reassessment result to client
```

## Security Architecture

- API keys loaded from environment only (never from request headers or frontend code)
- LLM evidence packet is treated as data, not instructions (system prompt says so explicitly)
- No real account actions executed — all "executions" are DB status updates only
- CI security scan rejects commits containing `sk-` keys or tracked `.env` files
- TigerGraph mock mode never silently passes as real; labeled in every response

## Scalability Notes (production path)

- SQLite → PostgreSQL: change `DATABASE_URL` only; ORM is database-agnostic
- Stateless FastAPI workers behind a load balancer
- LangGraph state can be checkpointed to Redis for distributed resumption
- TigerGraph handles graph traversal at billion-edge scale natively
