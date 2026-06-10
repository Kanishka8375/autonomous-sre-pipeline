import time
import logging
from sre_pipeline.pipeline_orchestrator import PipelineOrchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def main() -> None:
    log_dir = "/var/log/"
    webhook_url = "http://127.0.0.1:8000/v1/policy/validate"
    orchestrator = PipelineOrchestrator(log_dir, webhook_url, dry_run=True)
    
    logging.info("Starting Autonomous SRE Pipeline Loop (DRY-RUN MODE)...")
    while True:
        try:
            report = orchestrator.run()
            logging.info(f"Pipeline run complete: {report.anomalies_detected} anomalies, {report.actions_executed} executed.")
        except Exception as e:
            logging.error(f"Pipeline error: {e}")
        
        logging.info("Sleeping for 30s...")
        time.sleep(30)

if __name__ == "__main__":
    main()
