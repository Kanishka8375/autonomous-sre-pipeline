import httpx
import logging
from typing import Optional, Any, Dict
import json
import datetime
from pathlib import Path
from sre_pipeline.models import AnomalyEvent, PolicyDecision, PolicyRequest, PolicyVerdict, ActionType

DEFERRED_FILE = Path("sre_pipeline/deferred_queue.json")

class PolicyGateway:
    """Gateway to validate anomaly events against an external policy webhook."""
    
    def __init__(self, webhook_url: str) -> None:
        """Initialize with the policy webhook URL."""
        self.webhook_url: str = webhook_url
        self.logger: logging.Logger = logging.getLogger(__name__)

    def _is_already_deferred(self, service: str, rule_id: str) -> bool:
        if not DEFERRED_FILE.exists():
            return False
        queue = json.loads(DEFERRED_FILE.read_text())
        return any(
            v["service"] == service
            and v["rule_id"] == rule_id
            and v["status"] == "pending"
            for v in queue.values()
        )

    def _persist_deferred(
        self,
        request_id: str,
        anomaly: AnomalyEvent,
        decision: PolicyDecision
    ) -> None:
        if self._is_already_deferred(anomaly.context.get("service", "unknown"), anomaly.rule_id):
            self.logger.info("Duplicate deferred skipped: %s/%s already pending",
                        anomaly.context.get("service", "unknown"), anomaly.rule_id)
            return

        queue = json.loads(DEFERRED_FILE.read_text()) if DEFERRED_FILE.exists() else {}
        queue[request_id] = {
            "service": anomaly.context.get("service", "unknown"),
            "action": anomaly.proposed_action.value,
            "severity": anomaly.severity,
            "rule_id": anomaly.rule_id,
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "status": "pending"
        }
        DEFERRED_FILE.write_text(json.dumps(queue, indent=2))

    def evaluate(self, anomaly: AnomalyEvent) -> PolicyDecision:
        """Evaluate an anomaly against the policy and return a PolicyDecision."""
        request = PolicyRequest(
            action_type=anomaly.proposed_action,
            anomaly=anomaly,
            requester="sre_agent"
        )
        
        payload: Dict[str, Any] = {
            "action_type": anomaly.proposed_action.value,
            "requester": "sre_agent",
            "context": {
                "rule_id": anomaly.rule_id,
                "severity": anomaly.severity,
                "service": anomaly.context.get("service", "unknown")
            }
        }
        
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(self.webhook_url, json=payload)
                response.raise_for_status()
                
                data = response.json()
                verdict = PolicyVerdict(data.get("verdict", "denied"))
                
                approved_action: Optional[ActionType] = None
                if data.get("approved_action"):
                    approved_action = ActionType(data["approved_action"])
                    
                if verdict == PolicyVerdict.DEFERRED:
                    decision = PolicyDecision(
                        request=request,
                        verdict=PolicyVerdict.DEFERRED,
                        reason="awaiting_human_approval — logged to deferred_queue.json",
                        approved_action=None,
                        request_id=data.get("request_id")
                    )
                    if decision.request_id:
                        self._persist_deferred(decision.request_id, anomaly, decision)
                    return decision
                    
                return PolicyDecision(
                    request=request,
                    verdict=verdict,
                    reason=data.get("reason", ""),
                    approved_action=approved_action,
                    request_id=data.get("request_id")
                )
                
        except httpx.HTTPError as e:
            self.logger.warning("Policy webhook HTTP error: %s", e)
            return PolicyDecision(
                request=request,
                verdict=PolicyVerdict.DENIED,
                reason="policy_service_unavailable",
                approved_action=None
            )
        except (ValueError, KeyError) as e:
            self.logger.warning("Policy webhook response parsing error: %s", e)
            return PolicyDecision(
                request=request,
                verdict=PolicyVerdict.DENIED,
                reason="policy_service_unavailable",
                approved_action=None
            )

