import pytest
from sre_pipeline.pipeline_orchestrator import PipelineOrchestrator
from sre_pipeline.policy_gateway import PolicyGateway
from sre_pipeline.remediation_executor import RemediationExecutor
from sre_pipeline.anomaly_detector import AnomalyDetector
from sre_pipeline.models import LogEntry, LogLevel, AnomalyEvent, ActionType
import datetime

def test_pipeline_orchestrator() -> None:
    orchestrator = PipelineOrchestrator("logs", "http://localhost:8001/v1/policy/validate", dry_run=True, executor="systemctl")
    # Don't run it to avoid real HTTP requests, just instantiate
    assert orchestrator.policy_gateway.webhook_url == "http://localhost:8001/v1/policy/validate"
    assert orchestrator.remediation_executor.executor == "systemctl"

def test_policy_gateway() -> None:
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

def test_remediation_executor() -> None:
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

def test_pipeline_run(monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = PipelineOrchestrator("logs", "http://localhost:8001/v1/policy/validate", dry_run=True)
    from unittest.mock import MagicMock
    orchestrator.log_ingester.ingest = MagicMock(return_value=[  # type: ignore[method-assign]
        LogEntry(
            timestamp=datetime.datetime.now(),
            level=LogLevel.CRITICAL,
            service="test-service",
            message="Test",
            raw="",
            source_format="json"
        )
    ])
    # mock evaluate
    from unittest.mock import MagicMock
    orchestrator.policy_gateway.evaluate = MagicMock(side_effect=lambda x: PolicyDecision(  # type: ignore[method-assign]
        request=PolicyRequest(anomaly=x, action_type=ActionType.RESTART_SERVICE, requester="agent"),
        verdict=PolicyVerdict.APPROVED,
        reason="approved",
        approved_action=ActionType.RESTART_SERVICE,
        request_id="123"
    ))
    report = orchestrator.run()
    assert report.total_logs == 1
    assert report.actions_approved == 1

def test_policy_gateway_evaluate(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    gateway = PolicyGateway("http://localhost:8001/v1/policy/validate")
    import typing
    class MockClient:
        def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None: pass
        def __enter__(self) -> typing.Any: return self
        def __exit__(self, *args: typing.Any) -> None: pass
        def post(self, url: str, json: typing.Any) -> typing.Any:
            class MockResponse:
                def raise_for_status(self) -> None: pass
                def json(self) -> dict[str, str]: return {"verdict": "approved", "reason": "test"}
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
    
def test_policy_gateway_evaluate_denied(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx
    gateway = PolicyGateway("http://localhost:8001/v1/policy/validate")
    import typing
    class MockClient:
        def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None: pass
        def __enter__(self) -> typing.Any: return self
        def __exit__(self, *args: typing.Any) -> None: pass
        def post(self, url: str, json: typing.Any) -> typing.Any:
            class MockResponse:
                def raise_for_status(self) -> None: pass
                def json(self) -> dict[str, str]: return {"verdict": "denied", "reason": "policy failed"}
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

def test_anomaly_detector() -> None:
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
def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["sre_pipeline", "--logs", "logs", "--policy", "http://localhost:8001", "--interval", "0", "--dry-run"])
    # mock orchestrator.run
    import typing
    from sre_pipeline.models import PipelineReport
    class MockOrchestrator:
        def __init__(self, *args: typing.Any, **kwargs: typing.Any) -> None: pass
        def run(self) -> PipelineReport:
            from sre_pipeline.models import PipelineReport
            return PipelineReport(
                total_logs=8,
                anomalies_detected=3,
                actions_proposed=3,
                actions_approved=2,
                actions_denied=0,
                actions_deferred=1,
                actions_executed=0,
                results=[]
            )
    monkeypatch.setattr("sre_pipeline.__main__.PipelineOrchestrator", MockOrchestrator)
    main()
