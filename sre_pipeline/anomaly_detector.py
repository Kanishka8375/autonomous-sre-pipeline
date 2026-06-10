from typing import List, Callable, Any, Dict, Optional
from sre_pipeline.models import LogEntry, AnomalyEvent, LogLevel, ActionType

class AnomalyDetector:
    """Detects anomalies in log entries using configurable rules."""
    
    def __init__(self, rules: Optional[List[Dict[str, Any]]] = None) -> None:
        """Initialize with optional custom rules. If none provided, uses defaults."""
        if rules is not None:
            self.rules = rules
        else:
            self.rules = [
                {
                    "rule_id": "CRITICAL_LOG",
                    "condition": lambda e: e.level == LogLevel.CRITICAL,
                    "severity": 5,
                    "proposed_action": ActionType.RESTART_SERVICE
                },
                {
                    "rule_id": "HIGH_ERROR_RATE",
                    "condition": lambda e: e.level == LogLevel.ERROR and "timeout" in e.message,
                    "severity": 4,
                    "proposed_action": ActionType.RESTART_SERVICE
                },
                {
                    "rule_id": "SERVICE_WARN",
                    "condition": lambda e: e.level == LogLevel.WARNING,
                    "severity": 2,
                    "proposed_action": ActionType.ALERT_ONCALL
                }
            ]

    def detect(self, logs: List[LogEntry]) -> List[AnomalyEvent]:
        """Apply rules to logs and return detected anomalies."""
        events: List[AnomalyEvent] = []
        for log in logs:
            for rule in self.rules:
                condition: Callable[[LogEntry], bool] = rule["condition"]
                if condition(log):
                    events.append(
                        AnomalyEvent(
                            log_entry=log,
                            rule_id=rule["rule_id"],
                            severity=rule["severity"],
                            proposed_action=rule["proposed_action"],
                            context={"service": log.service}
                        )
                    )
                    break  # Stop evaluating rules for this log once an anomaly is found
        return events
