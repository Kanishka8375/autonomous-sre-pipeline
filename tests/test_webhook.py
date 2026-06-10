import pytest
from fastapi.testclient import TestClient
from sre_pipeline.webhook import app
from sre_pipeline.db import Database
import sre_pipeline.webhook

sre_pipeline.webhook.SERVICE_ALLOWLIST.update({"api-gateway", "db-primary", "test-service"})

client = TestClient(app)

from typing import Any
from unittest.mock import patch

@pytest.fixture
def test_db(tmp_path: Any) -> Database:
    db_path = str(tmp_path / "webhook_test.db")
    db_instance = Database(db_path=db_path)
    import sre_pipeline.webhook
    sre_pipeline.webhook.db = db_instance
    return db_instance

def test_validate_deferred_writes_to_sqlite(test_db: Database) -> None:
    response = client.post("/v1/policy/validate", json={
        "action_type": "restart_service",
        "requester": "sre_agent",
        "context": {
            "service": "db-primary",
            "rule_id": "CRITICAL_LOG",
            "severity": 5
        }
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "deferred"
    request_id = data["request_id"]
    
    pending = test_db.list_pending()
    assert len(pending) == 1
    assert pending[0].id == request_id
    assert pending[0].status == "pending"
    assert pending[0].service == "db-primary"

def test_approve_updates_sqlite(test_db: Database) -> None:
    # Setup deferred
    response = client.post("/v1/policy/validate", json={
        "action_type": "restart_service",
        "requester": "sre_agent",
        "context": {
            "service": "db-primary",
            "rule_id": "CRITICAL_LOG",
            "severity": 5
        }
    })
    request_id = response.json()["request_id"]
    
    assert len(test_db.list_pending()) == 1
    
    # Approve
    app_res = client.post(f"/v1/policy/approve/{request_id}")
    assert app_res.status_code == 200
    
    assert len(test_db.list_pending()) == 0
    
    # Check status
    status_res = client.get(f"/v1/policy/status/{request_id}")
    assert status_res.status_code == 200
    assert status_res.json()["verdict"] == "approved"
