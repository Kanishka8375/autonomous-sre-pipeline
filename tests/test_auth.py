import pytest
import os
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from sre_pipeline.auth import verify_api_key

app = FastAPI()

@app.get("/secure-endpoint", dependencies=[Depends(verify_api_key)])
def secure_endpoint() -> dict[str, str]:
    return {"status": "ok"}

client = TestClient(app)

def test_verify_api_key_success() -> None:
    os.environ["SRE_API_KEY"] = "super-secret-key"
    response = client.get("/secure-endpoint", headers={"X-API-Key": "super-secret-key"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    del os.environ["SRE_API_KEY"]

def test_verify_api_key_failure() -> None:
    os.environ["SRE_API_KEY"] = "super-secret-key"
    response = client.get("/secure-endpoint", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 403
    del os.environ["SRE_API_KEY"]

def test_verify_api_key_missing_header() -> None:
    os.environ["SRE_API_KEY"] = "super-secret-key"
    response = client.get("/secure-endpoint")
    assert response.status_code == 403
    del os.environ["SRE_API_KEY"]

def test_verify_api_key_not_configured() -> None:
    if "SRE_API_KEY" in os.environ:
        del os.environ["SRE_API_KEY"]
    response = client.get("/secure-endpoint", headers={"X-API-Key": "any-key"})
    assert response.status_code == 403
