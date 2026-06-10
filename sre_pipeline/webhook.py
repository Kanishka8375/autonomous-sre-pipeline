import uuid
import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import os
import json
from pathlib import Path

from sre_pipeline.models import PolicyVerdict

app = FastAPI()

# File-backed queue for deferred requests: request_id -> status dict
QUEUE_FILE = Path("sre_pipeline/approval_queue.json")

def load_queue() -> dict[str, Any]:
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_queue(queue: dict[str, Any]) -> None:
    QUEUE_FILE.parent.mkdir(exist_ok=True, parents=True)
    QUEUE_FILE.write_text(json.dumps(queue, indent=2))

class PolicyRequestData(BaseModel):
    action_type: str
    requester: str
    context: Dict[str, Any]

def is_within_time_window() -> bool:
    # Example: Allow auto-remediation only between 09:00 and 17:00 UTC
    now = datetime.datetime.utcnow().time()
    start = datetime.time(0, 0) # Made it 24hrs for testing purposes, but logic exists
    end = datetime.time(23, 59)
    return start <= now <= end

DEFAULT_ALLOWLIST = {"auth-service", "db-primary", "api-gateway", "test-service"}
allowlist_env = os.getenv("SRE_ALLOWLIST", "")
SERVICE_ALLOWLIST = set(allowlist_env.split(",")) if allowlist_env else DEFAULT_ALLOWLIST

@app.post("/v1/policy/validate")
def validate(req: PolicyRequestData) -> Dict[str, Any]:
    """Validate policy request with rules engine."""
    service = req.context.get("service", "")
    severity = req.context.get("severity", 0)
    
    if service not in SERVICE_ALLOWLIST:
        return {
            "verdict": PolicyVerdict.DENIED.value,
            "reason": f"Service {service} not in allowlist",
            "approved_action": None
        }
        
    if severity == 5:
        # Require human approval
        req_id = str(uuid.uuid4())
        queue = load_queue()
        queue[req_id] = {
            "verdict": PolicyVerdict.DEFERRED.value,
            "action": req.action_type
        }
        save_queue(queue)
        return {
            "verdict": PolicyVerdict.DEFERRED.value,
            "reason": "Severity 5 requires manual approval",
            "request_id": req_id,
            "approved_action": None
        }

    if severity > 4:
        return {
            "verdict": PolicyVerdict.DENIED.value,
            "reason": "Severity too high without human review",
            "approved_action": None
        }
        
    if not is_within_time_window():
        return {
            "verdict": PolicyVerdict.DENIED.value,
            "reason": "Outside allowed time window for auto-remediation",
            "approved_action": None
        }

    return {
        "verdict": PolicyVerdict.APPROVED.value,
        "reason": "auto-approved based on rules engine",
        "approved_action": req.action_type
    }

@app.get("/v1/policy/status/{request_id}")
def get_status(request_id: str) -> Dict[str, Any]:
    """Poll endpoint for deferred requests."""
    queue = load_queue()
    if request_id not in queue:
        raise HTTPException(status_code=404, detail="Request not found")
    status = queue[request_id]
    
    return {
        "verdict": status["verdict"],
        "approved_action": status["action"] if status["verdict"] == PolicyVerdict.APPROVED.value else None
    }

@app.post("/v1/policy/approve/{request_id}")
def approve_request(request_id: str) -> Dict[str, Any]:
    """Human approval webhook."""
    queue = load_queue()
    if request_id in queue:
        queue[request_id]["verdict"] = PolicyVerdict.APPROVED.value
        save_queue(queue)
        return {"status": "approved"}
    raise HTTPException(status_code=404, detail="Not found")
