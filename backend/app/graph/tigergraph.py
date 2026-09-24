import os
import httpx
import time
import random
from datetime import datetime, timedelta
from typing import Any


class TigerGraphClient:
    def __init__(self):
        self.host = os.getenv("TIGERGRAPH_HOST", "")
        self.username = os.getenv("TIGERGRAPH_USERNAME", "tigergraph")
        self.password = os.getenv("TIGERGRAPH_PASSWORD", "")
        self.graph = os.getenv("TIGERGRAPH_GRAPH", "FraudInvestigation")
        self.timeout = 5.0
        self.available = bool(self.host and self.password)

    async def _get(self, path: str) -> dict:
        if not self.available:
            return {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    f"{self.host}/restpp{path}",
                    auth=(self.username, self.password)
                )
                resp.raise_for_status()
                return resp.json()
        except Exception:
            return {}

    async def get_customer_neighborhood(self, customer_id: str) -> dict:
        start = time.time()
        if not self.available:
            return self._mock_customer_neighborhood(customer_id, time.time() - start)

        data = await self._get(f"/graph/{self.graph}/vertices/Customer/{customer_id}")
        if not data:
            return self._mock_customer_neighborhood(customer_id, time.time() - start)

        return {
            "customer_id": customer_id,
            "data": data,
            "is_mock": False,
            "latency_ms": round((time.time() - start) * 1000)
        }

    async def get_transaction_history(self, account_id: str, days: int = 30) -> dict:
        start = time.time()
        if not self.available:
            return self._mock_transaction_history(account_id, days, time.time() - start)
        data = await self._get(f"/graph/{self.graph}/edges/Account/{account_id}/MADE_TRANSACTION")
        if not data:
            return self._mock_transaction_history(account_id, days, time.time() - start)
        return {"account_id": account_id, "transactions": data, "is_mock": False, "latency_ms": round((time.time() - start) * 1000)}

    async def find_connected_entities(self, customer_id: str) -> dict:
        start = time.time()
        if not self.available:
            return self._mock_connected_entities(customer_id, time.time() - start)
        data = await self._get(f"/query/{self.graph}/find_connected_entities?customerId={customer_id}")
        if not data:
            return self._mock_connected_entities(customer_id, time.time() - start)
        return {"customer_id": customer_id, "entities": data, "is_mock": False, "latency_ms": round((time.time() - start) * 1000)}

    async def find_shared_devices(self, customer_id: str) -> dict:
        start = time.time()
        if not self.available:
            return self._mock_shared_devices(customer_id, time.time() - start)
        data = await self._get(f"/query/{self.graph}/find_shared_devices?customerId={customer_id}")
        if not data:
            return self._mock_shared_devices(customer_id, time.time() - start)
        return {"customer_id": customer_id, "shared_devices": data, "is_mock": False, "latency_ms": round((time.time() - start) * 1000)}

    async def find_similar_cases(self, case_features: dict) -> dict:
        start = time.time()
        if not self.available:
            return self._mock_similar_cases(case_features, time.time() - start)
        return self._mock_similar_cases(case_features, time.time() - start)

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.available:
            return {}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.host}/restpp{path}",
                    json=payload,
                    auth=(self.username, self.password)
                )
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {"error": str(e)}

    async def write_case_to_graph(self, case_data: dict) -> dict:
        if not self.available:
            return {"success": False, "is_mock": True, "reason": "TigerGraph not configured"}

        case_id = case_data.get("case_id", "")
        customer_id = case_data.get("customer_id", "")
        risk_level = case_data.get("risk_level", "LOW")
        status = case_data.get("status", "UNKNOWN")
        patterns = case_data.get("fraud_patterns", [])

        # Upsert Case vertex
        case_vertex_payload = {
            "vertices": {
                "Case": {
                    case_id: {
                        "status": {"value": status},
                        "risk_level": {"value": risk_level},
                        "fraud_patterns": {"value": ",".join(patterns)},
                        "created_at": {"value": case_data.get("created_at", "")},
                    }
                }
            }
        }

        result = await self._post(f"/graph/{self.graph}", case_vertex_payload)
        if result.get("error"):
            return {"success": False, "is_mock": False, "error": result["error"]}

        # Upsert edge: Customer -INVOLVED_IN-> Case (if customer exists in graph)
        if customer_id:
            edge_payload = {
                "edges": {
                    "Customer": {
                        customer_id: {
                            "INVOLVED_IN": {
                                "Case": {
                                    case_id: {}
                                }
                            }
                        }
                    }
                }
            }
            await self._post(f"/graph/{self.graph}", edge_payload)

        return {"success": True, "is_mock": False, "case_id": case_id}

    # ── Mock data generators ──────────────────────────────────────────────

    def _mock_customer_neighborhood(self, customer_id: str, elapsed: float) -> dict:
        seed_map = {
            "C-001": {"risk_signals": ["shared_device_with_3_accounts", "rapid_velocity", "new_ip_address"],
                      "account_age_days": 180, "kyc_status": "VERIFIED", "credit_score": 650},
            "C-002": {"risk_signals": ["first_large_transaction", "limited_history"],
                      "account_age_days": 12, "kyc_status": "PENDING", "credit_score": None},
            "C-003": {"risk_signals": ["new_device_login", "geography_mismatch", "rapid_transfers"],
                      "account_age_days": 720, "kyc_status": "VERIFIED", "credit_score": 780},
        }
        profile = seed_map.get(customer_id, {
            "risk_signals": [],
            "account_age_days": random.randint(30, 1000),
            "kyc_status": "VERIFIED",
            "credit_score": random.randint(600, 800)
        })
        return {
            "customer_id": customer_id,
            "profile": profile,
            "connected_accounts": self._get_connected_accounts(customer_id),
            "is_mock": True,
            "latency_ms": round(elapsed * 1000)
        }

    def _get_connected_accounts(self, customer_id: str) -> list:
        if customer_id == "C-001":
            return [
                {"account_id": "A-001", "relationship": "PRIMARY"},
                {"account_id": "A-002", "relationship": "SHARED_DEVICE", "suspicious": True},
                {"account_id": "A-003", "relationship": "SHARED_DEVICE", "suspicious": True},
                {"account_id": "A-004", "relationship": "SHARED_DEVICE", "suspicious": True},
            ]
        elif customer_id == "C-003":
            return [{"account_id": "A-010", "relationship": "PRIMARY"}]
        return [{"account_id": f"A-{customer_id[-3:]}", "relationship": "PRIMARY"}]

    def _mock_transaction_history(self, account_id: str, days: int, elapsed: float) -> dict:
        now = datetime.utcnow()
        tx_map = {
            "A-001": [
                {"tx_id": "TX-1001", "amount": 4800.0, "merchant": "Wire Transfer", "timestamp": (now - timedelta(hours=2)).isoformat(), "destination": "A-002"},
                {"tx_id": "TX-1002", "amount": 4900.0, "merchant": "Wire Transfer", "timestamp": (now - timedelta(hours=1, minutes=45)).isoformat(), "destination": "A-003"},
                {"tx_id": "TX-1003", "amount": 4750.0, "merchant": "Wire Transfer", "timestamp": (now - timedelta(hours=1, minutes=30)).isoformat(), "destination": "A-004"},
            ],
            "A-002": [
                {"tx_id": "TX-2001", "amount": 4800.0, "merchant": "Crypto Exchange", "timestamp": (now - timedelta(hours=1)).isoformat(), "destination": "EXTERNAL"},
            ],
            "A-010": [
                {"tx_id": "TX-3001", "amount": 12500.0, "merchant": "International Wire", "timestamp": (now - timedelta(hours=3)).isoformat(), "destination": "FOREIGN"},
                {"tx_id": "TX-3002", "amount": 8900.0, "merchant": "ATM Withdrawal", "timestamp": (now - timedelta(hours=2)).isoformat(), "destination": "CASH"},
            ],
        }
        transactions = tx_map.get(account_id, [
            {"tx_id": f"TX-{account_id}", "amount": random.uniform(100, 5000), "merchant": "General Merchant",
             "timestamp": (now - timedelta(days=random.randint(1, days))).isoformat()}
        ])
        return {"account_id": account_id, "transactions": transactions, "days": days, "is_mock": True, "latency_ms": round(elapsed * 1000)}

    def _mock_connected_entities(self, customer_id: str, elapsed: float) -> dict:
        entity_map = {
            "C-001": {
                "shared_devices": [{"device_id": "D-001", "accounts_count": 4, "suspicious": True}],
                "shared_ips": [{"ip": "192.168.1.100", "accounts_count": 4, "suspicious": True}],
                "linked_accounts": ["A-001", "A-002", "A-003", "A-004"],
            },
            "C-003": {
                "shared_devices": [{"device_id": "D-NEW-001", "accounts_count": 1, "is_new": True}],
                "shared_ips": [{"ip": "10.20.30.40", "accounts_count": 1, "geo": "Eastern Europe"}],
                "linked_accounts": ["A-010"],
            }
        }
        entities = entity_map.get(customer_id, {"shared_devices": [], "shared_ips": [], "linked_accounts": []})
        return {"customer_id": customer_id, "entities": entities, "is_mock": True, "latency_ms": round(elapsed * 1000)}

    def _mock_shared_devices(self, customer_id: str, elapsed: float) -> dict:
        if customer_id == "C-001":
            return {
                "customer_id": customer_id,
                "shared_devices": [
                    {"device_id": "D-001", "fingerprint": "abc123", "accounts": ["A-001", "A-002", "A-003", "A-004"],
                     "suspicious": True, "reason": "4 accounts share same device fingerprint"}
                ],
                "is_mock": True, "latency_ms": round(elapsed * 1000)
            }
        return {"customer_id": customer_id, "shared_devices": [], "is_mock": True, "latency_ms": round(elapsed * 1000)}

    def _mock_similar_cases(self, features: dict, elapsed: float) -> dict:
        similar = [
            {"case_id": "HIST-001", "similarity": 0.92, "outcome": "FRAUD_CONFIRMED",
             "pattern": "MONEY_LAUNDERING", "action_taken": "block_account",
             "description": "Connected account ring used shared device for structured transfers"},
            {"case_id": "HIST-002", "similarity": 0.78, "outcome": "FRAUD_CONFIRMED",
             "pattern": "ACCOUNT_TAKEOVER", "action_taken": "block_account",
             "description": "New device login followed by rapid large transfers"},
            {"case_id": "HIST-003", "similarity": 0.65, "outcome": "CLEARED",
             "pattern": "VELOCITY_ABUSE", "action_taken": "monitor_account",
             "description": "High velocity resolved after customer verification"},
        ]
        return {"similar_cases": similar, "is_mock": True, "latency_ms": round(elapsed * 1000)}
