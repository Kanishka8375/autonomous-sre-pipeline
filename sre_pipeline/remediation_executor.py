import logging
import datetime
import subprocess
from typing import List
from sre_pipeline.models import PolicyDecision, RemediationResult, ActionType, PolicyVerdict

class RemediationExecutor:
    """Executes policy-approved remediation actions."""

    def __init__(self, dry_run: bool = False, executor: str = "systemctl") -> None:
        self.logger = logging.getLogger(__name__)
        self.dry_run = dry_run
        self.executor = executor

    def execute_all(self, decisions: List[PolicyDecision]) -> List[RemediationResult]:
        """Execute a list of policy decisions."""
        results: List[RemediationResult] = []
        for decision in decisions:
            if decision.verdict == PolicyVerdict.DEFERRED:
                results.append(RemediationResult(
                    decision=decision,
                    executed=False,
                    outcome="deferred_pending_human_approval",
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                ))
                continue
            results.append(self.execute(decision))
        return results

    def execute(self, decision: PolicyDecision) -> RemediationResult:
        """Execute a single policy decision."""
        if decision.verdict != PolicyVerdict.APPROVED or not decision.approved_action:
            self.logger.info("Action denied or missing approved_action, not executing.")
            return RemediationResult(
                decision=decision,
                executed=False,
                outcome="Not executed due to policy denial",
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

        service = decision.request.anomaly.context.get("service", "unknown")
        action = decision.approved_action

        if self.dry_run:
            outcome = f"[DRY-RUN] Would have executed: {action.value} on {service}"
            self.logger.info(outcome)
            return RemediationResult(
                decision=decision,
                executed=False,
                outcome=outcome,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )

        if action == ActionType.RESTART_SERVICE:
            try:
                if self.executor == "docker":
                    import docker
                    client = docker.from_env()
                    client.containers.get(service).restart()
                    outcome = f"Restarted service {service} via Docker API"
                else:
                    subprocess.run(["systemctl", "restart", service], check=True, capture_output=True)
                    outcome = f"Restarted service {service} via systemctl"
                self.logger.info(outcome)
            except Exception as e:
                outcome = f"Failed to restart {service}: {e}"
                self.logger.error(outcome)
                return RemediationResult(
                    decision=decision,
                    executed=False,
                    outcome=outcome,
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
        elif action == ActionType.SCALE_UP:
            outcome = f"Simulated scale-up for {service}"
            self.logger.info(outcome)
        elif action == ActionType.ALERT_ONCALL:
            outcome = f"Simulated oncall alert for {service}"
            self.logger.info(outcome)
        elif action == ActionType.ROLLBACK:
            outcome = f"Simulated rollback for {service}"
            self.logger.info(outcome)
        elif action == ActionType.NO_ACTION:
            outcome = "No action taken"
            self.logger.info(outcome)
        else:
            outcome = f"Unknown action: {action}"
            self.logger.warning(outcome)

        return RemediationResult(
            decision=decision,
            executed=True,
            outcome=outcome,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
