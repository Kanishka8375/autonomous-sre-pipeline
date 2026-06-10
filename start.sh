fuser -k 8001/tcp || true
for pid in $(pgrep -f "sre_pipeline"); do if [ "$pid" != "$$" ] && [ "$pid" != "$PPID" ]; then kill -9 $pid || true; fi; done
sleep 2
nohup python3 -m uvicorn sre_pipeline.webhook:app --host 127.0.0.1 --port 8001 > webhook.log 2>&1 &
sleep 3
nohup python3 -m sre_pipeline --logs logs --policy http://127.0.0.1:8001/v1/policy/validate --dry-run --interval 30 > pipeline.log 2>&1 &
