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
    actions_deferred: int
    actions_executed: int
    results: list[RemediationResult]

class NotificationChannel(str, Enum):
    SLACK = "slack"
    EMAIL = "email"
    NONE = "none"

@dataclass
class AnomalyFingerprint:
    """Unique identity of an anomaly pattern for dedup and adaptive baseline."""
    service: str
    rule_id: str
    hour_of_day: int          # 0–23, for time-window baselines
    day_of_week: int          # 0–6
    fingerprint_hash: str     # sha256(service+rule_id+message_template)

@dataclass
class AdaptiveThreshold:
    """Rolling baseline for a service+rule combination."""
    fingerprint: AnomalyFingerprint
    rolling_count: int        # events in last N windows
    baseline_mean: float      # expected events per window
    baseline_std: float       # standard deviation
    current_severity: int     # dynamically computed 1–5
    last_updated: datetime.datetime

@dataclass
class PlaybookStep:
    """Single step in a remediation playbook."""
    order: int
    action: ActionType
    condition: Optional[str]  # Python expression string, evaluated at runtime
    timeout_seconds: int = 30

@dataclass
class Playbook:
    """Versioned remediation playbook for a rule."""
    rule_id: str
    version: str
    steps: list[PlaybookStep]
    requires_human_approval: bool
    max_auto_executions_per_hour: int = 3

@dataclass
class AuditRecord:
    """Immutable audit log entry — every decision recorded."""
    id: str
    timestamp: datetime.datetime
    pipeline_run_id: str
    service: str
    rule_id: str
    severity: int
    verdict: PolicyVerdict
    action_taken: Optional[ActionType]
    executed: bool
    dry_run: bool
    executor: str
    duration_ms: float
    fingerprint_hash: str
