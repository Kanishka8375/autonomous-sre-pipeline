from fastapi.testclient import TestClient
from sre_pipeline.webhook import app, db
print("Initial DB Path:", db.db_path)
client = TestClient(app)
res = client.post("/v1/policy/validate", json={
    "action_type": "restart_service",
    "requester": "sre_agent",
    "context": {
        "service": "db-primary",
        "rule_id": "CRITICAL_LOG",
        "severity": 5
    }
})
print("Status Code:", res.status_code)
print("Response:", res.json())
print("Pending in default db:", len(db.list_pending()))
