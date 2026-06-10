#!/bin/bash
set -e

mkdir -p logs

# Start services
uvicorn sre_pipeline.webhook:app --host 127.0.0.1 --port 8001 > webhook.log 2>&1 &
sleep 2

# Inject test logs
rm -f logs/demo.log
echo '{"timestamp":"2026-06-10T12:00:00Z","level":"ERROR","service":"auth-service","message":"Connection timeout"}' >> logs/demo.log
echo '{"timestamp":"2026-06-10T12:00:01Z","level":"CRITICAL","service":"db-primary","message":"Disk at 99%"}' >> logs/demo.log
echo '{"timestamp":"2026-06-10T12:00:02Z","level":"WARNING","service":"api-gateway","message":"Memory high"}' >> logs/demo.log

# Run one pipeline pass
python3 -m sre_pipeline --logs logs --policy http://127.0.0.1:8001/v1/policy/validate --dry-run --interval 0 --executor systemctl

# Show deferred queue
echo "--- Deferred (severity 5, awaiting human) ---"
cat sre_pipeline/deferred_queue.json
