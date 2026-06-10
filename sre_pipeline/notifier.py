import os
import json
import logging
import urllib.request
import urllib.error
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class Notifier(ABC):
    @abstractmethod
    def send_notification(self, message: str) -> bool:
        pass

class SlackNotifier(Notifier):
    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.webhook_url = os.getenv("SLACK_WEBHOOK_URL")

    def send_notification(self, message: str) -> bool:
        if not self.webhook_url:
            logger.warning("SLACK_WEBHOOK_URL not set. Skipping notification.")
            return False

        payload = {"text": message}
        
        if self.dry_run:
            logger.info("DRY RUN: Would send to Slack: %s", payload)
            return True

        try:
            req = urllib.request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.info("Successfully sent Slack notification.")
                    return True
                else:
                    logger.error("Failed to send Slack notification. Status: %s", response.status)
                    return False
        except urllib.error.URLError as e:
            logger.error("Error sending Slack notification: %s", e)
            return False
