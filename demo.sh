#!/bin/bash
set -e

mkdir -p logs

# Clean up previous state
rm -f logs/demo.log
rm -f logs/.positions.json
rm -f sre_pipeline/sre.db

# Start services
uvicorn sre_pipeline.webhook:app --host 127.0.0.1 --port 8001 > webhook.log 2>&1 &
UVICORN_PID=$!
sleep 2

# Inject test logs
echo '{"timestamp":"2026-06-10T12:00:00Z","level":"ERROR","service":"auth-service","message":"Connection timeout"}' >> logs/demo.log
echo '{"timestamp":"2026-06-10T12:00:01Z","level":"CRITICAL","service":"db-primary","message":"Disk at 99%"}' >> logs/demo.log
echo '{"timestamp":"2026-06-10T12:00:02Z","level":"WARNING","service":"api-gateway","message":"Memory high"}' >> logs/demo.log

# Run one pipeline pass
python3 -m sre_pipeline --logs logs --policy http://127.0.0.1:8001/v1/policy/validate --dry-run --interval 0 --executor systemctl

# Cleanup background processes
kill $UVICORN_PID 2>/dev/null || true
