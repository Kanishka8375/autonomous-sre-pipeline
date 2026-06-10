# Autonomous SRE Pipeline

An autonomous agent that ingests logs, detects anomalies using configurable rules, validates actions through a rules-engine policy gateway, and executes remediations.

## Quickstart (Docker Compose)

The easiest way to run the pipeline is with Docker Compose. This starts both the **Policy Webhook Service** and the **SRE Agent** container.

1. **Create a logs directory** and add some sample logs:
   ```bash
   mkdir logs
   echo '2025-01-15 10:23:45 ERROR auth-service Connection timeout' > logs/test.log
   ```

2. **Start the stack**:
   ```bash
   docker-compose up --build
   ```

3. **Observe**:
   - The policy service runs at `http://localhost:8001`.
   - The agent continually scans the mounted `./logs` directory every 15 seconds.
   - Any log matching anomalous patterns will trigger an action request, which the policy service approves, denies, or defers.

## Running Locally via CLI

You can also run the agent natively using Python:

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Start the Policy Service (in a separate terminal)**:
   ```bash
   uvicorn sre_pipeline.webhook:app --host 127.0.0.1 --port 8001
   ```

3. **Start the Agent**:
   ```bash
   python -m sre_pipeline --logs /path/to/your/logs --policy http://127.0.0.1:8001/v1/policy/validate --dry-run
   ```

### Options for CLI:
- `--logs <dir>`: Path to the directory containing logs to parse.
- `--policy <url>`: URL of the policy validation webhook.
- `--dry-run`: Evaluate actions and log them, but don't actually execute the remediation (e.g., `systemctl`).
- `--interval <sec>`: Time between pipeline execution loops (default 30s).
- `--executor <systemctl|docker>`: Execution method for remediations (default systemctl).

## Known Limitations

- **systemctl executor**: Requires a systemd-enabled host. Fails gracefully
  in standard Docker containers (exit code 5, logged, pipeline continues).
  Use `--executor docker` for containerized fleets.

- **Human approval queue**: Severity-5 actions are deferred and persisted to
  `deferred_queue.json`. Resolution requires manual API call. No notification
  system (email/Slack) is included — this is a local tool.

- **In-memory webhook state**: The FastAPI policy service loses runtime state
  on restart. `deferred_queue.json` persists deferred requests, but the
  in-memory approval_queue dict does not survive a webhook restart.

- **Log formats**: Supports structured JSON and plaintext with configurable
  regex. Binary logs, compressed `.gz` files, and journald binary format
  are skipped silently.
