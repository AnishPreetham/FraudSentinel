# GSQL query templates for TigerGraph

FIND_CONNECTED_ENTITIES = """
CREATE QUERY find_connected_entities(VERTEX<Customer> customerId) FOR GRAPH FraudInvestigation {
  SetAccum<VERTEX> @@connectedAccounts;
  SetAccum<VERTEX> @@sharedDevices;

  start = {customerId};

  accounts = SELECT a FROM start:c -(HAS_ACCOUNT)-> Account:a
    ACCUM @@connectedAccounts += a;

  devices = SELECT d FROM accounts:a -(USED_DEVICE)-> Device:d
    ACCUM @@sharedDevices += d;

  PRINT @@connectedAccounts, @@sharedDevices;
}
"""

FIND_FRAUD_RING = """
CREATE QUERY find_fraud_ring(VERTEX<Customer> startCustomer, INT depth = 3) FOR GRAPH FraudInvestigation {
  OrAccum @visited;

  seeds = {startCustomer};
  result = SELECT v FROM seeds:s -(ANY:e)-> :v
    WHERE NOT v.@visited
    ACCUM v.@visited += TRUE
    LIMIT depth * 100;

  PRINT result;
}
"""

GET_TRANSACTION_VELOCITY = """
CREATE QUERY get_transaction_velocity(VERTEX<Account> accountId, DATETIME startTime) FOR GRAPH FraudInvestigation {
  SumAccum<DOUBLE> @@totalAmount;
  SumAccum<INT> @@txCount;

  transactions = SELECT t FROM accountId:a -(MADE_TRANSACTION)-> Transaction:t
    WHERE t.timestamp >= startTime
    ACCUM @@totalAmount += t.amount, @@txCount += 1;

  PRINT @@totalAmount AS total_amount, @@txCount AS tx_count;
}
"""
