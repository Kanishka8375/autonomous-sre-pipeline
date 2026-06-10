from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Any
import datetime

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ActionType(str, Enum):
    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    ALERT_ONCALL = "alert_oncall"
    ROLLBACK = "rollback"
    NO_ACTION = "no_action"

class PolicyVerdict(str, Enum):
    APPROVED = "approved"
    DENIED = "denied"
    DEFERRED = "deferred"

@dataclass
class LogEntry:
    timestamp: datetime.datetime
    level: LogLevel
    service: str
    message: str
    raw: str
    source_format: str  # "json" | "plaintext"

@dataclass
class AnomalyEvent:
    log_entry: LogEntry
    rule_id: str
    severity: int          # 1–5
    proposed_action: ActionType
    context: dict[str, Any]

@dataclass
class PolicyRequest:
    action_type: ActionType
    anomaly: AnomalyEvent
    requester: str = "sre_agent"

@dataclass
class PolicyDecision:
    request: PolicyRequest
    verdict: PolicyVerdict
    reason: str
    approved_action: Optional[ActionType] = None
    request_id: Optional[str] = None

@dataclass
class RemediationResult:
    decision: PolicyDecision
    executed: bool
    outcome: str
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.utcnow)

@dataclass
class PipelineReport:
    total_logs: int
    anomalies_detected: int
    actions_proposed: int
    actions_approved: int
    actions_denied: int
    actions_executed: int
    results: list[RemediationResult]
