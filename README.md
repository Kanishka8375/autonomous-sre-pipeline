# autonomous-sre-pipeline

> Local autonomous SRE agent — ingests logs, detects anomalies, and gates 
> all remediation actions through a policy webhook before execution.

![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-v0.1.1-orange)

## What it does

1. **Ingests** structured JSON and plaintext logs from a local directory  
2. **Detects** anomalies using configurable rule-based thresholds  
3. **Gates** every remediation action through a policy webhook — nothing 
   executes without approval  
4. **Defers** severity-5 actions to a human approval queue persisted to disk  
5. **Executes** approved actions via systemctl or Docker  

## Quickstart

```bash
git clone https://github.com/Kanishka8375/autonomous-sre-pipeline
cd autonomous-sre-pipeline
pip install -r requirements.txt
./demo.sh
```

## Demo output

```text
[DRY-RUN] Pipeline run complete: 3 anomalies, 2 approved, 1 deferred, 0 executed.
--- Deferred (severity 5, awaiting human) ---
{
  "bdb32589": {
    "service": "db-primary",
    "action": "restart_service",
    "severity": 5,
    "status": "pending"
  }
}
```

## Architecture

```text
LogIngester → AnomalyDetector → PolicyGateway → RemediationExecutor
                                      ↓
                              policy webhook
                              (approve/deny/defer)
                                      ↓
                              deferred_queue.json
                              (human approval)
```

## CLI

```bash
python -m sre_pipeline \
  --logs /var/log/myapp \
  --policy http://127.0.0.1:8001 \
  --executor systemctl \
  --interval 30 \
  --dry-run
```

## Known Limitations

- `systemctl` executor requires a systemd host — fails gracefully in standard Docker containers
- Human approval queue requires manual API call — no notification system
- Webhook state is in-memory — deferred_queue.json persists to disk
- Binary and compressed log formats are skipped silently
