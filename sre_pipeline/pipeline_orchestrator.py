from sre_pipeline.log_ingester import LogIngester
from sre_pipeline.anomaly_detector import AnomalyDetector
from sre_pipeline.policy_gateway import PolicyGateway
from sre_pipeline.remediation_executor import RemediationExecutor
from sre_pipeline.models import PipelineReport, PolicyVerdict

class PipelineOrchestrator:
    """Orchestrates the entire SRE pipeline from ingestion to remediation."""

    def __init__(self, log_directory: str, webhook_url: str, dry_run: bool = False, executor: str = "systemctl") -> None:
        self.log_ingester = LogIngester(log_directory)
        self.anomaly_detector = AnomalyDetector()
        self.policy_gateway = PolicyGateway(webhook_url)
        self.remediation_executor = RemediationExecutor(dry_run=dry_run, executor=executor)

    def run(self) -> PipelineReport:
        """Run the end-to-end pipeline."""
        # Phase 1: Ingest Logs
        logs = self.log_ingester.ingest()
        
        # Phase 2: Detect Anomalies
        anomalies = self.anomaly_detector.detect(logs)
        
        # Phase 3: Policy Validation
        decisions = []
        actions_approved = 0
        actions_denied = 0
        actions_deferred = 0
        
        for anomaly in anomalies:
            decision = self.policy_gateway.evaluate(anomaly)
            
            if decision.verdict == PolicyVerdict.DEFERRED:
                self.policy_gateway.logger.info("Decision deferred for %s — logged to deferred_queue.json", decision.request_id)
                actions_deferred += 1
                
            decisions.append(decision)
            if decision.verdict == PolicyVerdict.APPROVED:
                actions_approved += 1
            elif decision.verdict == PolicyVerdict.DENIED:
                actions_denied += 1
                
        # Phase 4: Remediation Execution
        results = self.remediation_executor.execute_all(decisions)
        actions_executed = sum(1 for r in results if r.executed)
        
        return PipelineReport(
            total_logs=len(logs),
            anomalies_detected=len(anomalies),
            actions_proposed=len(anomalies),
            actions_approved=actions_approved,
            actions_denied=actions_denied,
            actions_deferred=actions_deferred,
            actions_executed=actions_executed,
            results=results
        )
