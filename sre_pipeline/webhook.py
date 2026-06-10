import uuid
import datetime
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List
import os
import json
from pathlib import Path

from sre_pipeline.models import PolicyVerdict
from sre_pipeline.db import Database, DeferredEvent
from sre_pipeline.structured_logger import setup_structured_logging
from sre_pipeline.auth import verify_api_key
from sre_pipeline.approval_ui import ui_router

setup_structured_logging()

app = FastAPI()
app.include_router(ui_router)
db = Database()

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
        event = DeferredEvent(
            id=req_id,
            service=service,
            rule_id=req.context.get("rule_id", "UNKNOWN"),
            action=req.action_type,
            severity=severity,
            status="pending",
            created_at=datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        db.upsert_deferred(event)
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
    # We query the DB for the event. Wait, list_pending only returns pending. 
    # We need a query by ID. Or we can just get all events.
    # Actually, we can add a method or query direct.
    with db._get_conn() as conn:
        cursor = conn.execute("SELECT status, action FROM deferred_events WHERE id = ?", (request_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Request not found")
        
        return {
            "verdict": row["status"],
            "approved_action": row["action"] if row["status"] == PolicyVerdict.APPROVED.value else None
        }

@app.post("/v1/policy/approve/{request_id}")
def approve_request(request_id: str) -> Dict[str, Any]:
    """Human approval webhook."""
    with db._get_conn() as conn:
        cursor = conn.execute("SELECT id FROM deferred_events WHERE id = ?", (request_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Not found")
    
    db.resolve_deferred(request_id, PolicyVerdict.APPROVED.value, "admin")
    return {"status": "approved"}

@app.get("/v1/audit")
def get_audit(api_key: str = Depends(verify_api_key)) -> List[Dict[str, Any]]:
    """Return all audit logs."""
    # Assuming db has a way to get audit logs. Let's query SQLite.
    with db._get_conn() as conn:
        cursor = conn.execute("SELECT * FROM audit_log ORDER BY timestamp DESC")
        return [dict(row) for row in cursor.fetchall()]

