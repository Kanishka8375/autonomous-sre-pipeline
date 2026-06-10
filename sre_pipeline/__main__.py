import argparse
import time
import logging
import sys
from .pipeline_orchestrator import PipelineOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous SRE Pipeline Agent")
    parser.add_argument("--logs", required=True, help="Path to the directory containing logs")
    parser.add_argument("--policy", required=True, help="URL of the policy webhook")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no actual remediation)")
    parser.add_argument("--executor", choices=["systemctl", "docker"], default="systemctl", help="Execution method for remediations")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds")
    
    args = parser.parse_args()
    
    orchestrator = PipelineOrchestrator(args.logs, args.policy, dry_run=args.dry_run, executor=args.executor)
    
    logging.info(f"Starting SRE Agent monitoring '{args.logs}'...")
    logging.info(f"Policy gateway: {args.policy}")
    logging.info(f"Dry-run mode: {args.dry_run}, Executor: {args.executor}")
    
    while True:
        try:
            report = orchestrator.run()
            logging.info(
                f"Pipeline run complete: {report.anomalies_detected} anomalies detected, "
                f"{report.actions_approved} approved, {report.actions_executed} executed."
            )
        except Exception as e:
            logging.error(f"Pipeline error: {e}")
        
        if args.interval == 0:
            break
        logging.info(f"Sleeping for {args.interval}s...")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
