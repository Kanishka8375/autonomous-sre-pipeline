import argparse
import time
import logging
import sys
from .pipeline_orchestrator import PipelineOrchestrator

from .structured_logger import setup_structured_logging

setup_structured_logging(level=logging.INFO)

def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomous SRE Pipeline Agent")
    parser.add_argument("--logs", default="logs", help="Path to the directory containing logs")
    parser.add_argument("--source", choices=["files", "journald", "docker", "nginx", "syslog"], default="files")
    parser.add_argument("--report", action="store_true", help="Print 24-hour report and exit")
    parser.add_argument("--policy", default="http://127.0.0.1:8001/v1/policy/validate", help="URL of the policy webhook")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (no actual remediation)")
    parser.add_argument("--executor", choices=["systemctl", "docker"], default="systemctl", help="Execution method for remediations")
    parser.add_argument("--interval", type=int, default=30, help="Polling interval in seconds")
    
    args = parser.parse_args()
    
    if getattr(args, "report", False):
        print_report()
        return
        
    import subprocess
    import os
    if args.source == "journald":
        os.makedirs(args.logs, exist_ok=True)
        log_file = open(os.path.join(args.logs, "journald.log"), "a")
        subprocess.Popen([
            "journalctl", "-f", "-o", "json",
            "--output-fields=SYSLOG_IDENTIFIER,PRIORITY,MESSAGE"
        ], stdout=log_file)

    if args.source == "docker":
        os.makedirs(args.logs, exist_ok=True)
        log_file = open(os.path.join(args.logs, "docker.log"), "a")
        subprocess.Popen([
            "docker", "events", "--filter", "type=container",
            "--format", "{{json .}}"
        ], stdout=log_file)

    if args.source == "nginx":
        args.logs = "/var/log/nginx"

    if args.source == "syslog":
        args.logs = "/var/log"
    
    orchestrator = PipelineOrchestrator(args.logs, args.policy, dry_run=args.dry_run, executor=args.executor)
    
    logging.info(f"Starting SRE Agent monitoring '{args.logs}'...")
    logging.info(f"Policy gateway: {args.policy}")
    logging.info(f"Dry-run mode: {args.dry_run}, Executor: {args.executor}")
    
    while True:
        try:
            report = orchestrator.run()
            mode = "DRY-RUN" if args.dry_run else "LIVE"
            logging.info(
                f"[{mode}] Pipeline run complete: {report.anomalies_detected} anomalies, "
                f"{report.actions_approved} approved, {report.actions_deferred} deferred, "
                f"{report.actions_executed} executed."
            )
        except Exception as e:
            logging.error(f"Pipeline error: {e}")
        
        if args.interval == 0:
            break
        logging.info(f"Sleeping for {args.interval}s...")
        time.sleep(args.interval)

def print_report() -> None:
    from sre_pipeline.db import Database
    db = Database()
    
    print("═══════════════════════════════════════")
    print("SRE PIPELINE — 24 HOUR REPORT")
    print("═══════════════════════════════════════")
    
    with db._get_conn() as conn:
        cursor = conn.execute("SELECT status, action, severity, service FROM deferred_events WHERE created_at >= datetime('now', '-1 day')")
        deferred = cursor.fetchall()
        cursor = conn.execute("SELECT action, status, service, details FROM audit_log WHERE timestamp >= datetime('now', '-1 day')")
        audit = cursor.fetchall()
        
    total_anomalies = len(deferred) + len(audit)
    print(f"Anomalies detected:        {total_anomalies}")
    
    sev5 = [d for d in deferred if d["severity"] == 5]
    print(f"  → Severity 5:             {len(sev5)}  (deferred — awaiting human)")
    
    print("\\nTop offending services:")
    services: dict[str, int] = {}
    for row in audit + deferred:
        s = row["service"]
        services[s] = services.get(s, 0) + 1
    
    for s, count in sorted(services.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  {s:<16} {count} events")
        
    print("\\nActions that WOULD have executed in live mode:")
    actions: dict[str, int] = {}
    for row in audit:
        a = row["action"]
        actions[a] = actions.get(a, 0) + 1
    
    for a, count in sorted(actions.items(), key=lambda x: x[1], reverse=True):
        print(f"  {a:<17} {count}x")
        
    print(f"\\nEstimated time saved: ~{total_anomalies * 0.1:.1f} hours of manual log monitoring")
    print("═══════════════════════════════════════")

if __name__ == "__main__":
    main()
