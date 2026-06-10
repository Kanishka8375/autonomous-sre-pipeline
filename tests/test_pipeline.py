import pytest
from sre_pipeline.pipeline_orchestrator import PipelineOrchestrator
from sre_pipeline.policy_gateway import PolicyGateway
from sre_pipeline.remediation_executor import RemediationExecutor
from sre_pipeline.anomaly_detector import AnomalyDetector
from sre_pipeline.models import LogEntry, LogLevel, AnomalyEvent, ActionType
import datetime

def test_pipeline_orchestrator():
    orchestrator = PipelineOrchestrator("logs", "http://localhost:8001/v1/policy/validate", dry_run=True, executor="systemctl")
    # Don't run it to avoid real HTTP requests, just instantiate
    assert orchestrator.policy_gateway.webhook_url == "http://localhost:8001/v1/policy/validate"
    assert orchestrator.remediation_executor.executor == "systemctl"

def test_policy_gateway():
    gateway = PolicyGateway("http://localhost:8001/v1/policy/validate")
    # Test duplicate logic
    anomaly = AnomalyEvent(
        log_entry=LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        ),
        rule_id="TEST_RULE_UNIQUE_ABC",
        severity=5,
        proposed_action=ActionType.RESTART_SERVICE,
        context={"service": "test-service"}
    )
    assert gateway._is_already_deferred("test-service", "TEST_RULE_UNIQUE_ABC") == False

from sre_pipeline.models import PolicyDecision, PolicyRequest, PolicyVerdict

def test_remediation_executor():
    executor = RemediationExecutor(dry_run=True, executor="systemctl")
    anomaly = AnomalyEvent(
        log_entry=LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        ),
        rule_id="TEST_RULE",
        severity=5,
        proposed_action=ActionType.RESTART_SERVICE,
        context={"service": "test-service"}
    )
    decision = PolicyDecision(
        request=PolicyRequest(anomaly=anomaly, action_type=ActionType.RESTART_SERVICE, requester="agent"),
        verdict=PolicyVerdict.APPROVED,
        reason="approved",
        approved_action=ActionType.RESTART_SERVICE,
        request_id="123"
    )
    # Dry run should return executed=False
    res = executor.execute(decision)
    assert res.executed == False
    assert "DRY-RUN" in res.outcome

    # Test denied decision
    denied = PolicyDecision(
        request=decision.request,
        verdict=PolicyVerdict.DENIED,
        reason="denied"
    )
    res_denied = executor.execute(denied)
    assert res_denied.executed == False

def test_pipeline_run(monkeypatch):
    orchestrator = PipelineOrchestrator("logs", "http://localhost:8001/v1/policy/validate", dry_run=True)
    orchestrator.log_ingester.ingest = lambda: [
        LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        )
    ]
    # mock evaluate
    orchestrator.policy_gateway.evaluate = lambda x: PolicyDecision(
        request=PolicyRequest(anomaly=x, action_type=ActionType.RESTART_SERVICE, requester="agent"),
        verdict=PolicyVerdict.APPROVED,
        reason="approved",
        approved_action=ActionType.RESTART_SERVICE,
        request_id="123"
    )
    report = orchestrator.run()
    assert report.total_logs == 1
    assert report.actions_approved == 1

def test_policy_gateway_evaluate(monkeypatch):
    import httpx
    gateway = PolicyGateway("http://localhost:8001/v1/policy/validate")
    class MockClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            class MockResponse:
                def raise_for_status(self): pass
                def json(self): return {"verdict": "approved", "reason": "test"}
            return MockResponse()
    monkeypatch.setattr(httpx, "Client", MockClient)
    
    anomaly = AnomalyEvent(
        log_entry=LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        ),
        rule_id="TEST_RULE",
        severity=4,
        proposed_action=ActionType.RESTART_SERVICE,
        context={"service": "test-service"}
    )
    decision = gateway.evaluate(anomaly)
    assert decision.verdict == PolicyVerdict.APPROVED
    assert decision.reason == "test"
    
def test_policy_gateway_evaluate_denied(monkeypatch):
    import httpx
    gateway = PolicyGateway("http://localhost:8001/v1/policy/validate")
    class MockClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, json):
            class MockResponse:
                def raise_for_status(self): pass
                def json(self): return {"verdict": "denied", "reason": "policy failed"}
            return MockResponse()
    monkeypatch.setattr(httpx, "Client", MockClient)
    
    anomaly = AnomalyEvent(
        log_entry=LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        ),
        rule_id="TEST_RULE",
        severity=4,
        proposed_action=ActionType.RESTART_SERVICE,
        context={"service": "test-service"}
    )
    decision = gateway.evaluate(anomaly)
    assert decision.verdict == PolicyVerdict.DENIED

def test_anomaly_detector():
    detector = AnomalyDetector()
    logs = [
        LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Critical error",
            raw="",
            source_format="plaintext"
        )
    ]
    anomalies = detector.detect(logs)
    assert len(anomalies) == 1
    assert anomalies[0].severity == 5
    assert anomalies[0].proposed_action == ActionType.RESTART_SERVICE

from sre_pipeline.__main__ import main
import sys
def test_main(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["sre_pipeline", "--logs", "logs", "--policy", "http://localhost:8001", "--interval", "0", "--dry-run"])
    # mock orchestrator.run
    class MockOrchestrator:
        def __init__(self, *args, **kwargs): pass
        def run(self):
            from sre_pipeline.pipeline_orchestrator import PipelineReport
            return PipelineReport(0, 0, 0, 0)
    monkeypatch.setattr("sre_pipeline.__main__.PipelineOrchestrator", MockOrchestrator)
    main()
