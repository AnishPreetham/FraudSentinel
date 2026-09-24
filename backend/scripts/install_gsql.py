#!/usr/bin/env python
"""
Install FraudSentinel GSQL queries into TigerGraph.

Usage:
    python scripts/install_gsql.py

Requires:
    TIGERGRAPH_HOST, TIGERGRAPH_USERNAME, TIGERGRAPH_PASSWORD, TIGERGRAPH_GRAPH
    set in environment or .env file.

This script is safe to re-run — it uses CREATE OR REPLACE QUERY.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

HOST = os.getenv("TIGERGRAPH_HOST", "")
USER = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
PASS = os.getenv("TIGERGRAPH_PASSWORD", "")
GRAPH = os.getenv("TIGERGRAPH_GRAPH", "FraudInvestigation")


QUERIES = {
    "GetCustomerHistory": f"""
CREATE OR REPLACE QUERY GetCustomerHistory(STRING customer_id, INT tx_limit = 50)
FOR GRAPH {GRAPH} {{
  SumAccum<INT> @tx_count;

  start = {{Customer.*}};
  customers = SELECT c FROM start:c WHERE c.customer_id == customer_id;
  accounts = SELECT a FROM customers:c-(OWNS_ACCOUNT:e)-Account:a;
  transactions = SELECT t FROM accounts:a-(PERFORMED_TRANSACTION:e)-Transaction:t
    ORDER BY t.timestamp DESC LIMIT tx_limit;
  devices = SELECT d FROM transactions:t-(USES_DEVICE:e)-Device:d;

  PRINT customers, accounts, transactions, devices;
}}
""",
    "DetectFraudRings": f"""
CREATE OR REPLACE QUERY DetectFraudRings(STRING account_id, INT depth = 3)
FOR GRAPH {GRAPH} {{
  SetAccum<VERTEX> @@ring_members;

  start = {{Account.*}};
  seed = SELECT a FROM start:a WHERE a.account_id == account_id;
  @@ring_members += seed;

  FOREACH i IN RANGE[1, depth] DO
    seed = SELECT a2 FROM seed:a1-(SHARED_DEVICE:e)-Account:a2
      WHERE a2 NOT IN @@ring_members;
    @@ring_members += seed;
  END;

  ring = {{@@ring_members}};
  PRINT ring;
}}
""",
    "GetRelatedTransactions": f"""
CREATE OR REPLACE QUERY GetRelatedTransactions(STRING account_id, INT days = 30)
FOR GRAPH {GRAPH} {{
  DATETIME cutoff = now() - days * 86400;

  start = {{Account.*}};
  acct = SELECT a FROM start:a WHERE a.account_id == account_id;
  txns = SELECT t FROM acct:a-(PERFORMED_TRANSACTION:e)-Transaction:t
    WHERE t.timestamp >= cutoff
    ORDER BY t.timestamp DESC;

  linked_devices = SELECT d FROM txns:t-(USES_DEVICE:e)-Device:d;
  related_txns = SELECT t2 FROM linked_devices:d-(USES_DEVICE:re)-Transaction:t2
    WHERE t2.timestamp >= cutoff AND t2 NOT IN txns;

  PRINT txns, related_txns, linked_devices;
}}
""",
}


def main():
    if not HOST or not PASS:
        print("ERROR: TIGERGRAPH_HOST and TIGERGRAPH_PASSWORD must be set in environment or .env")
        print("       Cannot install GSQL queries without a TigerGraph connection.")
        sys.exit(1)

    auth = (USER, PASS)
    base = HOST.rstrip("/")

    print(f"Connecting to TigerGraph: {base}")
    print(f"Graph: {GRAPH}\n")

    installed = []
    failed = []

    with httpx.Client(auth=auth, timeout=30) as client:
        for name, gsql in QUERIES.items():
            print(f"Installing query: {name} ... ", end="", flush=True)
            try:
                resp = client.post(
                    f"{base}/gsqlserver/gsql/file",
                    content=gsql.encode(),
                    headers={"Content-Type": "text/plain"},
                )
                if resp.status_code == 200 and "error" not in resp.text.lower():
                    print("OK")
                    installed.append(name)
                else:
                    print(f"FAILED ({resp.status_code})")
                    print(f"  Response: {resp.text[:200]}")
                    failed.append(name)
            except httpx.RequestError as e:
                print(f"FAILED (connection error: {e})")
                failed.append(name)

        # Install all queries at once
        if installed:
            print(f"\nInstalling {len(installed)} queries ... ", end="", flush=True)
            install_gsql = "\n".join(
                f"INSTALL QUERY {name}" for name in installed
            )
            try:
                resp = client.post(
                    f"{base}/gsqlserver/gsql/file",
                    content=install_gsql.encode(),
                    headers={"Content-Type": "text/plain"},
                )
                if resp.status_code == 200:
                    print("OK")
                else:
                    print(f"WARNING ({resp.status_code}): {resp.text[:200]}")
            except httpx.RequestError as e:
                print(f"WARNING: install step failed ({e})")

    print(f"\nDone. Installed: {installed or 'none'} | Failed: {failed or 'none'}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
