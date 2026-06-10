import pytest
import os
from typing import Any
from sre_pipeline.notifier import SlackNotifier, Notifier

def test_slack_notifier_live(httpserver: Any) -> None:
    httpserver.expect_request("/webhook").respond_with_json({"status": "ok"})
    
    # Environment var for webhook url
    os.environ["SLACK_WEBHOOK_URL"] = httpserver.url_for("/webhook")
    
    notifier: Notifier = SlackNotifier(dry_run=False)
    success = notifier.send_notification("Test message")
    
    assert success is True
    assert len(httpserver.log) == 1
    
    del os.environ["SLACK_WEBHOOK_URL"]

def test_slack_notifier_dry_run(httpserver: Any) -> None:
    httpserver.expect_request("/webhook").respond_with_json({"status": "ok"})
    
    os.environ["SLACK_WEBHOOK_URL"] = httpserver.url_for("/webhook")
    
    notifier: Notifier = SlackNotifier(dry_run=True)
    success = notifier.send_notification("Dry run message")
    
    assert success is True
    assert len(httpserver.log) == 0  # No actual HTTP request made
    
    del os.environ["SLACK_WEBHOOK_URL"]

def test_slack_notifier_no_url() -> None:
    if "SLACK_WEBHOOK_URL" in os.environ:
        del os.environ["SLACK_WEBHOOK_URL"]
        
    notifier: Notifier = SlackNotifier(dry_run=False)
    success = notifier.send_notification("Should fail or ignore smoothly")
    assert success is False
