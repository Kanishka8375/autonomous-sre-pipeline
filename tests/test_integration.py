import pytest
from fastapi.testclient import TestClient
from sre_pipeline.webhook import app, db
from sre_pipeline.db import DeferredEvent
import sre_pipeline.webhook

sre_pipeline.webhook.SERVICE_ALLOWLIST.update({"api-gateway", "db-primary", "test-service"})

client = TestClient(app)

def test_end_to_end_flow() -> None:
    # 1. Trigger an anomaly via the policy endpoint
    payload = {
        "action_type": "restart_service",
        "requester": "sre_agent_test",
        "context": {
            "service": "api-gateway",
            "rule_id": "LATENCY_SPIKE",
            "severity": 5
        }
    }
    response = client.post("/v1/policy/validate", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert data["verdict"] == "deferred"
    request_id = data["request_id"]
    
    # 2. Verify it's in the DB queue
    pending = db.list_pending()
    assert len(pending) >= 1
    
    found = False
    for event in pending:
        if event.id == request_id:
            assert event.service == "api-gateway"
            assert event.rule_id == "LATENCY_SPIKE"
            found = True
            break
            
    assert found
    
    # 3. Approve the action
    approval_response = client.post(f"/v1/policy/approve/{request_id}")
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "approved"
    
    # 4. Verify it's removed from pending
    pending_after = db.list_pending()
    for event in pending_after:
        assert event.id != request_id
