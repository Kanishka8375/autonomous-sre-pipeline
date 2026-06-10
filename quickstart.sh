#!/bin/bash
set -euo pipefail

echo "=== SRE Pipeline Quickstart ==="
echo "This script needs: Python 3.10+, pip"
echo ""

# 1. Auto-detect Python
PYTHON=$(which python3 || which python)
$PYTHON --version

# 2. Install deps silently
$PYTHON -m pip install -r requirements.txt -q

# 3. Generate a random API key
export SRE_API_KEY=$($PYTHON -c "import secrets; print(secrets.token_hex(16))")
echo "API Key: $SRE_API_KEY"

# 4. Start webhook, wait for it to be ready
uvicorn sre_pipeline.webhook:app --host 127.0.0.1 --port 8001 &
WEBHOOK_PID=$!
until curl -sf http://127.0.0.1:8001/health > /dev/null; do sleep 1; done
echo "Policy webhook: ready"

# 5. Run one pipeline pass against generated logs
mkdir -p logs
$PYTHON simulate_logs.py --auto --log-file logs/quickstart.log

$PYTHON -m sre_pipeline \
  --source files \
  --logs logs \
  --policy http://127.0.0.1:8001/v1/policy/validate \
  --interval 0 \
  --dry-run

# 6. Show approval UI
echo ""
echo "Approval UI: http://127.0.0.1:8001/ui/queue?api_key=$SRE_API_KEY"

# 7. Cleanup
kill $WEBHOOK_PID 2>/dev/null || true
