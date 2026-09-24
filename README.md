# FraudSentinel — Agentic Fraud Investigation System
### HHGOA Hackathon Submission · TigerGraph + LangGraph + Anthropic Claude

An enterprise-grade agentic fraud investigation platform powered by TigerGraph graph analytics and a 14-node LangGraph state machine. Fully functional in demo/mock mode — no external credentials required.

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 20+
- (Optional) TigerGraph instance, Anthropic API key

### Backend (FastAPI + LangGraph)

```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp ../.env.example .env        # edit with your credentials (all optional)
uvicorn app.main:app --reload --port 8000
```

API: http://localhost:8000  
Interactive docs: http://localhost:8000/docs  
Health check: http://localhost:8000/health

### Frontend (React + Vite + Tailwind)

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173

### Docker (both services)

```bash
cp .env.example .env           # edit as needed
docker-compose up --build
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React + TypeScript + Vite + Tailwind CSS)    │
│  • Investigation dashboard     • Evidence submission     │
│  • Approval workflow UI        • Network graph viz       │
└───────────────────────┬─────────────────────────────────┘
                        │ REST/JSON
┌───────────────────────▼─────────────────────────────────┐
│  FastAPI Backend  (async, SQLAlchemy + aiosqlite)        │
│  /api/cases   /api/demo   /health   /ready               │
└──────┬──────────────────────────┬───────────────────────┘
       │                          │
┌──────▼───────┐          ┌───────▼─────────────────────┐
│  LangGraph   │          │  SQLite / PostgreSQL         │
│  14-node     │          │  • Cases + Evidence          │
│  State       │          │  • Case Memory (similarity)  │
│  Machine     │          └──────────────────────────────┘
└──────┬───────┘
       │ parallel calls
┌──────▼──────────────────────────────────────────────────┐
│  Integration Layer                                       │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ TigerGraph REST  │  │ Anthropic Claude API          │ │
│  │ • Graph queries  │  │ • LLM case summary synthesis  │ │
│  │ • Vertex/edge    │  │ • Deterministic fallback      │ │
│  │   upserts        │  │   when key not configured     │ │
│  │ • Mock when not  │  └──────────────────────────────┘ │
│  │   configured     │                                   │
│  └──────────────────┘                                   │
└─────────────────────────────────────────────────────────┘
```

### LangGraph Workflow (14 nodes)

```
receive_case → retrieve_history → collect_evidence → detect_patterns
    → assess_uncertainty → [enough confidence?]
        → YES: recommend_action → check_approval → execute_action
               → explain_decision → update_case → write_memory → END
        → NO: request_additional_evidence → END (AWAITING_EVIDENCE)
                   ↑ POST /evidence triggers resume_investigation()
                   └── 7-node resume workflow → write_memory → END
```

**Key design decisions:**
- Policy engine is fully deterministic — never delegates risk decisions to LLM
- LLM only synthesizes natural-language summaries from a structured evidence packet
- Evidence pause is genuine: workflow halts at `AWAITING_EVIDENCE`, resumes via separate API call
- All integrations explicitly labeled: `real` / `mock` / `deterministic_fallback`

---

## Demo Scenarios

Navigate to http://localhost:5173 and click **Run Scenario**:

| Scenario | Pattern | Expected Action | Approval? |
|----------|---------|-----------------|-----------|
| A — Connected Fraud Ring | Money Laundering + Velocity Abuse | `block_account` | Human approval required |
| B — Ambiguous New Customer | Insufficient evidence | `request_additional_evidence` | Pauses for evidence |
| C — Account Takeover | Account Takeover | `block_account` | Human approval required |

All scenarios work without TigerGraph or Anthropic API keys.

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///./fraud_investigation.db` |
| `TIGERGRAPH_HOST` | TigerGraph server URL | _(mock mode)_ |
| `TIGERGRAPH_USERNAME` | TigerGraph username | `tigergraph` |
| `TIGERGRAPH_PASSWORD` | TigerGraph password | _(mock mode)_ |
| `TIGERGRAPH_GRAPH` | Graph name | `FraudInvestigation` |
| `ANTHROPIC_API_KEY` | Anthropic API key for LLM summaries | _(deterministic fallback)_ |
| `LLM_MODEL` | Claude model ID | `claude-haiku-4-5-20251001` |
| `CORS_ORIGINS` | Allowed frontend origins | `http://localhost:5173` |

### Mock vs. Real Mode

The `/ready` endpoint always reports which integrations are active:

```json
{
  "ready": true,
  "mode": "demo_mock",
  "integrations": {
    "tigergraph": "mock",
    "llm": "deterministic_fallback",
    "database": "sqlite"
  }
}
```

| `mode` | TigerGraph | LLM |
|--------|-----------|-----|
| `full` | real | real |
| `llm_only` | mock | real |
| `graph_only` | real | fallback |
| `demo_mock` | mock | fallback |

No silent fallbacks — if TigerGraph writes fail, the timeline step is labeled `graph write skipped (mock/unavailable)`.

---

## TigerGraph Integration

### Graph Schema

The system uses the `FraudInvestigation` graph with these vertex and edge types:

**Vertices:** `Customer`, `Account`, `Transaction`, `Device`, `IP_Address`, `Case`

**Edges:** `OWNS_ACCOUNT`, `PERFORMED_TRANSACTION`, `INVOLVED_IN`, `USES_DEVICE`, `FROM_IP`

### Installing GSQL Queries

```bash
cd backend
python scripts/install_gsql.py
```

This installs 3 pre-built GSQL queries:
- `GetCustomerHistory` — retrieves customer transaction history, connected accounts, and device fingerprints
- `DetectFraudRings` — traverses shared-device/IP relationships to identify connected fraud clusters
- `GetRelatedTransactions` — finds transactions linked by entity overlap within a time window

See [docs/tigergraph-schema.md](docs/tigergraph-schema.md) for full schema definition and query templates.

### Connecting to TigerGraph

```bash
# .env
TIGERGRAPH_HOST=https://your-instance.i.tgcloud.io
TIGERGRAPH_USERNAME=tigergraph
TIGERGRAPH_PASSWORD=your-password
TIGERGRAPH_GRAPH=FraudInvestigation
```

The client connects via TigerGraph's REST++ API using Basic Auth. If connection fails, the system continues in mock mode and logs the failure.

---

## Testing

```bash
cd backend
python -m pytest tests/ -v
```

**49 tests across 6 modules:**

| Module | Tests | What it covers |
|--------|-------|----------------|
| `test_policy.py` | 10 | Deterministic policy decisions, approval thresholds, compliance rules |
| `test_uncertainty.py` | 8 | Confidence scoring, evidence gap detection, uncertainty levels |
| `test_actions.py` | 9 | Next-best-action selection by pattern + confidence + risk level |
| `test_workflow.py` | 6 | Full end-to-end workflow for all 3 scenarios |
| `test_memory.py` | 5 | SQLite case memory storage, similarity retrieval, deduplication |
| `test_api.py` | 11 | FastAPI endpoints, demo scenarios, approval/rejection, 404 handling |

Run a specific module:

```bash
python -m pytest tests/test_policy.py -v
```

---

## Benchmark Runner

```bash
cd backend
python scripts/run_benchmark.py
```

Runs 20 synthetic test cases and produces:
- `outputs/benchmark/case_NN.json` — per-case investigation record
- `outputs/benchmark/benchmark_summary.json` — aggregate metrics
- `outputs/benchmark/benchmark_report.md` — formatted report

**Important:** The benchmark runs against synthetic cases unless you supply the official HHGOA dataset:

```bash
python scripts/run_benchmark.py --cases-dir /path/to/official/cases
```

Synthetic results are labeled `"is_synthetic": true` and the report explicitly warns they are not official benchmark results.

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) runs on every push:

1. **backend-tests** — Python 3.11, pytest with in-memory SQLite
2. **frontend-build** — Node 20, `tsc --noEmit`, `npm run build`
3. **security-scan** — checks for API keys in tracked files, verifies `.env` is not committed

---

## Project Structure

```
fraud-investigation/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── workflow.py        # 14-node LangGraph state machine
│   │   │   ├── llm.py             # Anthropic API + deterministic fallback
│   │   │   ├── evidence.py        # Evidence collection
│   │   │   ├── patterns.py        # Fraud pattern detection
│   │   │   ├── uncertainty.py     # Confidence scoring
│   │   │   ├── policy.py          # Deterministic policy engine
│   │   │   └── actions.py         # Next-best-action selection
│   │   ├── api/
│   │   │   ├── cases.py           # Case CRUD + approval + evidence submission
│   │   │   ├── demo.py            # Demo scenario endpoints
│   │   │   └── health.py          # /health + /ready
│   │   ├── db/                    # SQLAlchemy models + migrations
│   │   ├── graph/
│   │   │   ├── tigergraph.py      # TigerGraph REST client (real + mock)
│   │   │   └── gsql.py            # GSQL query templates
│   │   └── memory/
│   │       └── case_memory.py     # SQLite memory + Jaccard similarity
│   ├── tests/                     # 49 pytest tests
│   ├── scripts/
│   │   ├── run_benchmark.py       # 20-case benchmark runner
│   │   └── install_gsql.py        # GSQL query installer
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── api/                   # API client
│   │   └── types/                 # TypeScript types
│   └── package.json
├── docs/
│   ├── architecture.md            # System design details
│   ├── agent-workflow.md          # LangGraph node reference
│   ├── tigergraph-schema.md       # Graph schema + GSQL queries
│   └── demo-script.md             # Step-by-step demo guide
├── .github/workflows/ci.yml
├── .env.example
└── docker-compose.yml
```

---

## Hackathon Criteria

| Criterion | Weight | Implementation |
|-----------|--------|----------------|
| Investigation Accuracy | 25% | TigerGraph graph traversal + multi-source evidence with reliability scoring + similar-case memory retrieval |
| Next Best Action | 25% | Deterministic policy engine with confidence thresholds, risk tiers, and human approval gates |
| Agentic Design | 15% | 14-node LangGraph state machine with conditional branching, genuine evidence pause/resume, and parallel integration calls |
| Innovation | 15% | Uncertainty quantification, evidence gap detection, connected-entity ring detection, GraphRAG-style evidence synthesis |
| Case Summary & Explainability | 10% | Structured investigation timeline, Anthropic LLM summary (with deterministic fallback), supporting/contradicting evidence breakdown |
| Demo Quality | 10% | 3 end-to-end demo scenarios, real-time timeline, network visualization, human-in-the-loop approval UX |

---

## Known Limitations

- TigerGraph GSQL queries are templates; live graph traversal requires a running TigerGraph instance with the schema installed
- Anthropic LLM integration requires an `ANTHROPIC_API_KEY`; without it, summaries use the rule-based deterministic fallback (clearly labeled)
- Evidence collected during investigation uses mock TigerGraph data when credentials are absent — not fabricated as real
- Frontend evidence submission UI shows the AWAITING_EVIDENCE state but the submission form is minimal; a production UI would show richer guidance
- Benchmark results in `outputs/benchmark/` are from synthetic cases; official HHGOA dataset is required for competition scoring

## License

MIT
