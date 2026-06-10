import sqlite3
import datetime
from typing import Optional, Any
from dataclasses import dataclass
from sre_pipeline.models import AuditRecord, PolicyVerdict, ActionType

@dataclass
class DeferredEvent:
    id: str
    service: str
    rule_id: str
    action: str
    severity: int
    status: str
    created_at: str
    resolved_at: Optional[str] = None
    resolved_by: Optional[str] = None

class Database:
    def __init__(self, db_path: str = "sre_pipeline/sre.db") -> None:
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_conn() as conn:
            conn.executescript("""
CREATE TABLE IF NOT EXISTS deferred_events (
    id          TEXT PRIMARY KEY,
    service     TEXT NOT NULL,
    rule_id     TEXT NOT NULL,
    action      TEXT NOT NULL,
    severity    INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'pending',
    created_at  TEXT NOT NULL,
    resolved_at TEXT,
    resolved_by TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id              TEXT PRIMARY KEY,
    pipeline_run_id TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    service         TEXT NOT NULL,
    rule_id         TEXT NOT NULL,
    severity        INTEGER NOT NULL,
    verdict         TEXT NOT NULL,
    action_taken    TEXT,
    executed        INTEGER NOT NULL,
    dry_run         INTEGER NOT NULL,
    executor        TEXT NOT NULL,
    duration_ms     REAL NOT NULL,
    fingerprint_hash TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_deferred_status ON deferred_events(status);
CREATE INDEX IF NOT EXISTS idx_audit_service ON audit_log(service, rule_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
            """)

    def upsert_deferred(self, event: DeferredEvent) -> None:
        with self._get_conn() as conn:
            # Check if pending already exists for service + rule
            cursor = conn.execute(
                "SELECT id FROM deferred_events WHERE service = ? AND rule_id = ? AND status = 'pending'",
                (event.service, event.rule_id)
            )
            row = cursor.fetchone()
            if row and row["id"] != event.id:
                return
            
            conn.execute("""
                INSERT INTO deferred_events (id, service, rule_id, action, severity, status, created_at, resolved_at, resolved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    service=excluded.service,
                    rule_id=excluded.rule_id,
                    action=excluded.action,
                    severity=excluded.severity,
                    status=excluded.status,
                    created_at=excluded.created_at,
                    resolved_at=excluded.resolved_at,
                    resolved_by=excluded.resolved_by
            """, (event.id, event.service, event.rule_id, event.action, event.severity, event.status, event.created_at, event.resolved_at, event.resolved_by))

    def is_pending(self, service: str, rule_id: str) -> bool:
        with self._get_conn() as conn:
            cursor = conn.execute(
                "SELECT 1 FROM deferred_events WHERE service = ? AND rule_id = ? AND status = 'pending' LIMIT 1",
                (service, rule_id)
            )
            return cursor.fetchone() is not None

    def resolve_deferred(self, event_id: str, verdict: str, resolved_by: str) -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE deferred_events SET status = ?, resolved_at = ?, resolved_by = ? WHERE id = ?",
                (verdict, now, resolved_by, event_id)
            )

    def list_pending(self) -> list[DeferredEvent]:
        with self._get_conn() as conn:
            cursor = conn.execute("SELECT * FROM deferred_events WHERE status = 'pending'")
            return [DeferredEvent(**dict(row)) for row in cursor.fetchall()]

    def write_audit(self, record: AuditRecord) -> None:
        with self._get_conn() as conn:
            conn.execute("""
                INSERT INTO audit_log (
                    id, pipeline_run_id, timestamp, service, rule_id, severity, verdict, 
                    action_taken, executed, dry_run, executor, duration_ms, fingerprint_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id, record.pipeline_run_id, record.timestamp.isoformat(), record.service,
                record.rule_id, record.severity, record.verdict.value, 
                record.action_taken.value if record.action_taken else None,
                1 if record.executed else 0, 1 if record.dry_run else 0, record.executor, 
                record.duration_ms, record.fingerprint_hash
            ))

    def query_audit(
        self,
        service: Optional[str] = None,
        rule_id: Optional[str] = None,
        since: Optional[datetime.datetime] = None,
        limit: int = 100
    ) -> list[AuditRecord]:
        query = "SELECT * FROM audit_log WHERE 1=1"
        params: list[Any] = []
        if service:
            query += " AND service = ?"
            params.append(service)
        if rule_id:
            query += " AND rule_id = ?"
            params.append(rule_id)
        if since:
            query += " AND timestamp >= ?"
            params.append(since.isoformat())
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cursor = conn.execute(query, params)
            records = []
            for row in cursor.fetchall():
                d = dict(row)
                records.append(AuditRecord(
                    id=d["id"],
                    timestamp=datetime.datetime.fromisoformat(d["timestamp"]),
                    pipeline_run_id=d["pipeline_run_id"],
                    service=d["service"],
                    rule_id=d["rule_id"],
                    severity=d["severity"],
                    verdict=PolicyVerdict(d["verdict"]),
                    action_taken=ActionType(d["action_taken"]) if d["action_taken"] else None,
                    executed=bool(d["executed"]),
                    dry_run=bool(d["dry_run"]),
                    executor=d["executor"],
                    duration_ms=d["duration_ms"],
                    fingerprint_hash=d["fingerprint_hash"]
                ))
            return records
