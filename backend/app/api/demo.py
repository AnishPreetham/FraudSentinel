"""
Demo scenarios with pre-seeded data for hackathon presentation.
"""
from datetime import datetime, timedelta

SCENARIOS = {
    "scenario_a": {
        "id": "scenario_a",
        "title": "Connected Fraud Ring",
        "description": "Customer C-001 making structured wire transfers to 3 connected accounts sharing same device fingerprint. Classic money laundering ring.",
        "badge": "HIGH RISK",
        "badge_color": "red",
        "customer_id": "C-001",
        "account_id": "A-001",
        "trigger_type": "SUSPICIOUS_TRANSFER",
        "trigger_details": {
            "type": "suspicious_transfer",
            "amount": 14450.0,
            "destination_accounts": ["A-002", "A-003", "A-004"],
            "shared_device": True,
            "structured": True,
        },
        "expected_outcome": "block_account",
        "expected_patterns": ["MONEY_LAUNDERING", "VELOCITY_ABUSE"],
    },
    "scenario_b": {
        "id": "scenario_b",
        "title": "Ambiguous New Customer",
        "description": "Customer C-002 attempting first large transaction. Limited history, KYC pending. Agent requests step-up authentication — customer passes — transaction cleared.",
        "badge": "MEDIUM RISK",
        "badge_color": "yellow",
        "customer_id": "C-002",
        "account_id": "A-005",
        "trigger_type": "LARGE_FIRST_TRANSACTION",
        "trigger_details": {
            "type": "large_first_transaction",
            "amount": 8500.0,
            "merchant": "Jewelry Store",
            "kyc_pending": True,
        },
        "expected_outcome": "step_up_authentication",
        "expected_patterns": [],
    },
    "scenario_c": {
        "id": "scenario_c",
        "title": "Account Takeover",
        "description": "Customer C-003 (verified, good standing) suddenly logs in from new device in Eastern Europe, immediately initiates large transfers. Classic ATO pattern.",
        "badge": "CRITICAL",
        "badge_color": "red",
        "customer_id": "C-003",
        "account_id": "A-010",
        "trigger_type": "SUSPICIOUS_LOGIN",
        "trigger_details": {
            "type": "suspicious_login",
            "new_device": True,
            "new_geography": True,
            "location": "Eastern Europe",
            "ip": "10.20.30.40",
            "rapid_transfers_after_login": True,
        },
        "expected_outcome": "block_account",
        "expected_patterns": ["ACCOUNT_TAKEOVER"],
    },
}


def get_scenario(scenario_id: str) -> dict:
    return SCENARIOS.get(scenario_id)


def list_scenarios() -> list[dict]:
    return list(SCENARIOS.values())
