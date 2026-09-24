# TigerGraph Schema & GSQL Queries

## Graph: `FraudInvestigation`

### Vertex Types

| Vertex | Attributes |
|--------|-----------|
| `Customer` | `customer_id STRING`, `name STRING`, `kyc_status STRING`, `created_at DATETIME` |
| `Account` | `account_id STRING`, `account_type STRING`, `status STRING`, `balance DOUBLE` |
| `Transaction` | `transaction_id STRING`, `amount DOUBLE`, `currency STRING`, `timestamp DATETIME`, `channel STRING` |
| `Device` | `device_id STRING`, `device_type STRING`, `fingerprint STRING` |
| `IP_Address` | `ip STRING`, `country STRING`, `is_vpn BOOL` |
| `Case` | `case_id STRING`, `status STRING`, `risk_level STRING`, `fraud_patterns LIST<STRING>`, `created_at DATETIME` |

### Edge Types

| Edge | From → To | Attributes |
|------|-----------|-----------|
| `OWNS_ACCOUNT` | Customer → Account | `since DATETIME` |
| `PERFORMED_TRANSACTION` | Account → Transaction | — |
| `INVOLVED_IN` | Customer → Case | `role STRING` |
| `USES_DEVICE` | Transaction → Device | `last_used DATETIME` |
| `FROM_IP` | Transaction → IP_Address | — |
| `SHARED_DEVICE` | Account ↔ Account | `device_id STRING`, `count INT` |

---

## Installing the Schema

```bash
cd backend
python scripts/install_gsql.py
```

The script connects to TigerGraph using `TIGERGRAPH_HOST`, `TIGERGRAPH_USERNAME`, `TIGERGRAPH_PASSWORD`, and runs the schema DDL followed by the 3 query installations.

You can also run the GSQL directly:

```bash
gsql backend/app/graph/schema.gsql
```

---

## GSQL Queries

### 1. `GetCustomerHistory`

Retrieves a customer's full profile: accounts, recent transactions, linked devices, and IP addresses.

```sql
CREATE QUERY GetCustomerHistory(STRING customer_id, INT tx_limit = 50) FOR GRAPH FraudInvestigation {
  SumAccum<INT> @tx_count;
  
  start = {Customer.*};
  customers = SELECT c FROM start:c WHERE c.customer_id == customer_id;
  
  accounts = SELECT a FROM customers:c-(OWNS_ACCOUNT:e)-Account:a;
  
  transactions = SELECT t FROM accounts:a-(PERFORMED_TRANSACTION:e)-Transaction:t
    ORDER BY t.timestamp DESC LIMIT tx_limit;
  
  devices = SELECT d FROM transactions:t-(USES_DEVICE:e)-Device:d;
  
  PRINT customers, accounts, transactions, devices;
}
```

### 2. `DetectFraudRings`

Traverses shared-device and shared-IP relationships to identify connected fraud clusters.

```sql
CREATE QUERY DetectFraudRings(STRING account_id, INT depth = 3) FOR GRAPH FraudInvestigation {
  SetAccum<VERTEX> @@ring_members;
  
  start = {Account.*};
  seed = SELECT a FROM start:a WHERE a.account_id == account_id;
  @@ring_members += seed;
  
  FOREACH i IN RANGE[1, depth] DO
    seed = SELECT a2 FROM seed:a1-(SHARED_DEVICE:e)-Account:a2
      WHERE a2 NOT IN @@ring_members;
    @@ring_members += seed;
  END;
  
  ring = {@@ring_members};
  PRINT ring;
}
```

### 3. `GetRelatedTransactions`

Finds transactions linked by shared entity overlap within a configurable time window.

```sql
CREATE QUERY GetRelatedTransactions(STRING account_id, INT days = 30) FOR GRAPH FraudInvestigation {
  DATETIME cutoff = now() - days * 86400;
  
  start = {Account.*};
  acct = SELECT a FROM start:a WHERE a.account_id == account_id;
  
  txns = SELECT t FROM acct:a-(PERFORMED_TRANSACTION:e)-Transaction:t
    WHERE t.timestamp >= cutoff
    ORDER BY t.timestamp DESC;
  
  linked_devices = SELECT d FROM txns:t-(USES_DEVICE:e)-Device:d;
  
  related_txns = SELECT t2 FROM linked_devices:d-(USES_DEVICE:re)-Transaction:t2
    WHERE t2.timestamp >= cutoff AND t2 NOT IN txns;
  
  PRINT txns, related_txns, linked_devices;
}
```

---

## REST API Calls (used by `tigergraph.py`)

The backend calls TigerGraph via its REST++ API, authenticated with HTTP Basic Auth:

```
GET  /query/{graph}/GetCustomerHistory?customer_id=C-001
GET  /query/{graph}/DetectFraudRings?account_id=A-001
POST /graph/{graph}   (vertex/edge upsert)
```

When `TIGERGRAPH_HOST` is not configured, all calls return mock data and `is_mock: True` — no silent failures.

---

## Vertex Upsert (Case Write)

When an investigation completes, `write_case_to_graph()` upserts:

1. **Case vertex** — with `case_id`, `status`, `risk_level`, `fraud_patterns`
2. **INVOLVED_IN edge** — Customer → Case with `role: "subject"`

```json
POST /graph/FraudInvestigation
{
  "vertices": {
    "Case": {
      "CASE-001": {
        "status": {"value": "CLOSED"},
        "risk_level": {"value": "CRITICAL"},
        "fraud_patterns": {"value": ["MONEY_LAUNDERING"]}
      }
    }
  },
  "edges": {
    "Customer": {
      "C-001": {
        "INVOLVED_IN": {
          "Case": {
            "CASE-001": {"role": {"value": "subject"}}
          }
        }
      }
    }
  }
}
```
