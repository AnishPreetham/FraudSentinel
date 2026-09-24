#!/usr/bin/env python
"""
FraudSentinel Benchmark Runner — HHGOA Official 20-Case Evaluation

Usage:
    python scripts/run_benchmark.py [--cases-dir PATH] [--output-dir PATH]

The official benchmark dataset is NOT included in this repository.
If HHGOA_CASES_DIR is set and contains benchmark_cases.json (or case_*.json files),
those will be used. Otherwise, the runner executes against 20 synthetic test cases
clearly labeled as SYNTHETIC, not official benchmark results.

Output:
    outputs/benchmark/case_NN.json   — per-case investigation record
    outputs/benchmark/benchmark_summary.json
    outputs/benchmark/benchmark_report.md
"""

import asyncio
import json
import os
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path

# Allow running from scripts/ or backend/
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import init_db
from app.agent.workflow import run_investigation


# ── Synthetic test cases (used when official dataset is unavailable) ──────────

SYNTHETIC_CASES = [
    {
        "case_number": 1, "customer_id": "C-001", "account_id": "A-001",
        "trigger_type": "SUSPICIOUS_TRANSFER",
        "trigger": {"type": "suspicious_transfer", "amount": 14450.0, "shared_device": True, "structured": True},
        "description": "Connected fraud ring — 4 accounts sharing device",
        "is_synthetic": True,
    },
    {
        "case_number": 2, "customer_id": "C-003", "account_id": "A-010",
        "trigger_type": "SUSPICIOUS_LOGIN",
        "trigger": {"type": "suspicious_login", "new_device": True, "new_geography": True, "location": "Eastern Europe", "rapid_transfers_after_login": True},
        "description": "Account takeover — new device + geography + rapid transfers",
        "is_synthetic": True,
    },
    {
        "case_number": 3, "customer_id": "C-002", "account_id": "A-005",
        "trigger_type": "LARGE_FIRST_TRANSACTION",
        "trigger": {"type": "large_first_transaction", "amount": 8500.0, "kyc_pending": True},
        "description": "Ambiguous new customer — large first transaction",
        "is_synthetic": True,
    },
    {
        "case_number": 4, "customer_id": "C-004", "account_id": "A-020",
        "trigger_type": "VELOCITY_ALERT",
        "trigger": {"type": "velocity_alert", "rapid_velocity": True},
        "description": "High velocity transaction pattern",
        "is_synthetic": True,
    },
    {
        "case_number": 5, "customer_id": "C-005", "account_id": "A-030",
        "trigger_type": "MANUAL_REVIEW",
        "trigger": {"type": "manual_review"},
        "description": "Low-risk manual review case",
        "is_synthetic": True,
    },
]
# Extend to 20 synthetic cases
for i in range(6, 21):
    SYNTHETIC_CASES.append({
        "case_number": i,
        "customer_id": f"C-{i:03d}",
        "account_id": f"A-{i:03d}",
        "trigger_type": "SUSPICIOUS_TRANSFER" if i % 3 == 0 else "VELOCITY_ALERT" if i % 3 == 1 else "MANUAL_REVIEW",
        "trigger": {
            "type": "suspicious_transfer" if i % 3 == 0 else "velocity_alert" if i % 3 == 1 else "manual_review",
            "shared_device": i % 4 == 0,
            "structured": i % 5 == 0,
        },
        "description": f"Synthetic case {i}",
        "is_synthetic": True,
    })


def load_official_cases(cases_dir: Path) -> list[dict] | None:
    """Attempt to load official benchmark cases. Returns None if unavailable."""
    if not cases_dir.exists():
        return None

    # Try single combined file first
    combined = cases_dir / "benchmark_cases.json"
    if combined.exists():
        with open(combined) as f:
            data = json.load(f)
        print(f"[benchmark] Loaded {len(data)} official cases from {combined}")
        return data

    # Try individual case files
    case_files = sorted(cases_dir.glob("case_*.json"))
    if case_files:
        cases = []
        for cf in case_files:
            with open(cf) as f:
                cases.append(json.load(f))
        print(f"[benchmark] Loaded {len(cases)} official cases from {cases_dir}")
        return cases

    return None


async def run_case(case: dict, case_index: int, total: int) -> dict:
    case_id = f"BENCH-{case['case_number']:02d}"
    print(f"  [{case_index}/{total}] Running case {case_id}: {case.get('description', '')[:60]}")
    start = time.time()

    result = await run_investigation(
        case_id=case_id,
        customer_id=case["customer_id"],
        account_id=case["account_id"],
        trigger=case["trigger"],
    )

    elapsed = time.time() - start
    rec = result.get("recommendation", {})

    output = {
        "case_number": case["case_number"],
        "case_id": case_id,
        "is_synthetic": case.get("is_synthetic", False),
        "description": case.get("description", ""),
        "customer_id": case["customer_id"],
        "account_id": case["account_id"],
        "trigger_type": case["trigger_type"],
        # Investigation results
        "status": str(result.get("status", "")),
        "risk_level": result.get("risk_level", ""),
        "risk_score": round(result.get("risk_score", 0), 3),
        "confidence": round(result.get("confidence", 0), 3),
        "fraud_patterns": result.get("fraud_patterns", []),
        "evidence_count": len(result.get("evidence", [])),
        # Recommendation
        "recommended_action": rec.get("action", ""),
        "requires_approval": rec.get("requires_approval", False),
        "approver_role": rec.get("approver_role"),
        "execution_status": rec.get("execution_status", ""),
        "policy_basis": rec.get("policy_basis", ""),
        # Evidence
        "supporting_evidence": [
            {"source": e.get("source"), "content": e.get("content"), "reliability": e.get("reliability")}
            for e in result.get("evidence", []) if e.get("evidence_type") == "supporting"
        ],
        # Timeline
        "timeline_steps": len(result.get("timeline", [])),
        "investigation_timeline": result.get("timeline", []),
        # Summary
        "agent_reasoning": result.get("reasoning", ""),
        # Meta
        "elapsed_seconds": round(elapsed, 2),
        "error": result.get("error", ""),
        "graph_is_mock": result.get("graph_data", {}).get("is_mock", True),
        "run_timestamp": datetime.utcnow().isoformat(),
    }

    status_icon = "✓" if not output["error"] else "✗"
    print(f"         {status_icon} {output['risk_level']} risk | action={output['recommended_action']} | {elapsed:.1f}s")
    return output


async def main(cases_dir: Path, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    await init_db()

    # Load cases
    official_cases = load_official_cases(cases_dir)
    if official_cases:
        cases = official_cases
        dataset_source = "official"
        print(f"\n[benchmark] Using OFFICIAL dataset: {len(cases)} cases")
    else:
        cases = SYNTHETIC_CASES
        dataset_source = "synthetic"
        print(f"\n[benchmark] Official dataset not found at {cases_dir}")
        print(f"[benchmark] Using SYNTHETIC test cases (NOT official benchmark results)")
        print(f"[benchmark] To use official cases, set HHGOA_CASES_DIR or pass --cases-dir\n")

    total = len(cases)
    print(f"[benchmark] Running {total} cases...\n")

    results = []
    errors = []
    start_all = time.time()

    for i, case in enumerate(cases, 1):
        try:
            result = await run_case(case, i, total)
            results.append(result)
            # Write individual case file
            case_file = output_dir / f"case_{case['case_number']:02d}.json"
            with open(case_file, "w") as f:
                json.dump(result, f, indent=2)
        except Exception as e:
            errors.append({"case_number": case.get("case_number", i), "error": str(e)})
            print(f"  [ERROR] Case {i}: {e}")

    total_elapsed = time.time() - start_all

    # Summary metrics
    completed = [r for r in results if not r.get("error")]
    risk_dist = {}
    action_dist = {}
    for r in completed:
        risk_dist[r["risk_level"]] = risk_dist.get(r["risk_level"], 0) + 1
        action_dist[r["recommended_action"]] = action_dist.get(r["recommended_action"], 0) + 1

    summary = {
        "run_timestamp": datetime.utcnow().isoformat(),
        "dataset_source": dataset_source,
        "total_cases": total,
        "completed": len(completed),
        "errors": len(errors),
        "total_elapsed_seconds": round(total_elapsed, 2),
        "avg_elapsed_seconds": round(total_elapsed / max(total, 1), 2),
        "risk_distribution": risk_dist,
        "action_distribution": action_dist,
        "cases_requiring_approval": sum(1 for r in completed if r.get("requires_approval")),
        "cases_auto_executed": sum(1 for r in completed if r.get("execution_status") == "AUTO_EXECUTED"),
        "graph_mode": "mock" if all(r.get("graph_is_mock", True) for r in completed) else "mixed/real",
        "error_list": errors,
        "NOTE": (
            "Results are from SYNTHETIC test cases, not the official HHGOA benchmark dataset."
            if dataset_source == "synthetic"
            else "Results are from the official HHGOA benchmark dataset."
        ),
    }

    with open(output_dir / "benchmark_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    # Markdown report
    lines = [
        "# FraudSentinel Benchmark Report",
        f"\n**Run:** {summary['run_timestamp']}",
        f"**Dataset:** {dataset_source.upper()}"
        + (" ⚠️ Synthetic — NOT official results" if dataset_source == "synthetic" else " ✅ Official"),
        f"**Cases:** {summary['completed']}/{summary['total_cases']} completed | {summary['errors']} errors",
        f"**Total time:** {summary['total_elapsed_seconds']}s | Avg: {summary['avg_elapsed_seconds']}s/case",
        f"**Graph mode:** {summary['graph_mode']}",
        "",
        "## Risk Distribution",
        "| Risk Level | Count |",
        "|-----------|-------|",
    ]
    for level in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        lines.append(f"| {level} | {risk_dist.get(level, 0)} |")

    lines += [
        "",
        "## Action Distribution",
        "| Action | Count |",
        "|--------|-------|",
    ]
    for action, count in sorted(action_dist.items(), key=lambda x: -x[1]):
        lines.append(f"| {action} | {count} |")

    lines += [
        "",
        "## Approval Summary",
        f"- Cases requiring human approval: {summary['cases_requiring_approval']}",
        f"- Cases auto-executed: {summary['cases_auto_executed']}",
        "",
        "## Case Results",
        "| # | Customer | Risk | Action | Approval | Time |",
        "|---|----------|------|--------|----------|------|",
    ]
    for r in results:
        lines.append(
            f"| {r['case_number']} | {r['customer_id']} | {r['risk_level']} "
            f"| {r['recommended_action']} | {'Yes' if r['requires_approval'] else 'Auto'} "
            f"| {r['elapsed_seconds']}s |"
        )

    if errors:
        lines += ["", "## Errors", "| Case | Error |", "|------|-------|"]
        for e in errors:
            lines.append(f"| {e['case_number']} | {e['error']} |")

    if dataset_source == "synthetic":
        lines += [
            "",
            "## ⚠️ Note on Results",
            "These results are from **synthetic test cases** generated for development purposes.",
            "They are NOT the official HHGOA benchmark results.",
            "To run against the official dataset:",
            "1. Obtain the HHGOA benchmark cases from the competition organizers",
            "2. Place them in a directory as `benchmark_cases.json` or `case_NN.json` files",
            "3. Run: `python scripts/run_benchmark.py --cases-dir /path/to/official/cases`",
        ]

    with open(output_dir / "benchmark_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[benchmark] Complete: {summary['completed']}/{total} cases")
    print(f"[benchmark] Output: {output_dir}")
    print(f"[benchmark] Dataset: {dataset_source.upper()}")
    if dataset_source == "synthetic":
        print("[benchmark] ⚠️  These are SYNTHETIC results, NOT official benchmark results")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FraudSentinel Benchmark Runner")
    parser.add_argument(
        "--cases-dir",
        type=Path,
        default=Path(os.getenv("HHGOA_CASES_DIR", "benchmark_cases")),
        help="Directory containing official benchmark case files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("../outputs/benchmark"),
        help="Output directory for results",
    )
    args = parser.parse_args()
    asyncio.run(main(args.cases_dir, args.output_dir))
