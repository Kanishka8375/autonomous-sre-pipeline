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

## What this agent will do

✓ Read log files — never modifies them
✓ POST to your policy webhook before ANY action
✓ Log every decision to SQLite audit table
✓ In dry-run mode: only logs what it WOULD do

## What this agent will NOT do without your explicit approval

✗ Restart any service (requires policy webhook approval)
✗ Execute any command (blocked until webhook returns "approved")
✗ Do anything on severity-5 events (always requires human via /ui/queue)

## Safe to run right now

Start in dry-run mode — zero system impact, full visibility:
```bash
# For nginx users:
python -m sre_pipeline --source nginx --dry-run

# For Docker users:
python -m sre_pipeline --source docker --dry-run

# For systemd users:
python -m sre_pipeline --source journald --dry-run
```

Start with visibility and triage automation, prove value with measurable metrics, and expand to autonomous remediation as your team's confidence grows. 

## Value Reporting

Someone runs it for 24 hours in dry-run. They want to know: was it worth it?

```bash
python -m sre_pipeline --report
```

Output:
```text
═══════════════════════════════════════
SRE PIPELINE — 24 HOUR REPORT
═══════════════════════════════════════
Logs processed:        14,823
Anomalies detected:        47
  → Severity 1-2:          31  (alert_oncall)
  → Severity 3-4:          14  (restart_service)
  → Severity 5:             2  (deferred — awaiting human)

Top offending services:
  auth-service     23 events  (HIGH_ERROR_RATE x18, SERVICE_WARN x5)
  db-primary        2 events  (CRITICAL_LOG x2) ← needs your attention

Actions that WOULD have executed in live mode:
  restart_service   14x  ← each one = manual intervention saved
  alert_oncall      31x

Estimated time saved: ~4.2 hours of manual log monitoring
═══════════════════════════════════════
```

## Known Limitations

- `systemctl` executor requires a systemd host — fails gracefully in standard Docker containers
- Human approval queue requires manual API call — no notification system
- Webhook state is in-memory — deferred_queue.json persists to disk
- Binary and compressed log formats are skipped silently
