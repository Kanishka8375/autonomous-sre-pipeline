import pytest
from fastapi.testclient import TestClient
from sre_pipeline.webhook import app
from sre_pipeline.db import Database, DeferredEvent

client = TestClient(app)

def test_pending_ui_loads() -> None:
    import os
    os.environ["SRE_API_KEY"] = "super-secret-key"
    response = client.get("/ui/queue?api_key=super-secret-key")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Pending Approvals" in response.text
    del os.environ["SRE_API_KEY"]
