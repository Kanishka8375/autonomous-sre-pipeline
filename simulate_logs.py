"""
Real-time log simulator for SRE agent testing.
Generates realistic log patterns including anomaly bursts.
"""
import json
import time
import random
import datetime
import argparse
from pathlib import Path

SERVICES = ["auth-service", "api-gateway", "db-primary", "cache-service"]

NORMAL_MESSAGES = [
    "Request processed in {n}ms",
    "Cache hit ratio {n}%",
    "Connection pool size: {n}",
    "Healthcheck passed",
    "User session created",
    "Query executed in {n}ms",
]

ANOMALY_SCENARIOS = {
    "timeout_storm": {
        "level": "ERROR",
        "service": "auth-service",
        "messages": [
            "Connection timeout after 30s",
            "Connection timeout after 45s",
            "Upstream timeout after 30s",
        ],
        "count": 10,
        "description": "Timeout storm — triggers HIGH_ERROR_RATE rule"
    },
    "disk_critical": {
        "level": "CRITICAL",
        "service": "db-primary",
        "messages": [
            "Disk usage at 99%",
            "Write failed: no space left on device",
        ],
        "count": 1,
        "description": "Disk critical — triggers CRITICAL_LOG rule, severity 5"
    },
    "memory_warn": {
        "level": "WARNING",
        "service": "cache-service",
        "messages": [
            "Memory usage high: 87%",
            "Eviction rate increasing",
        ],
        "count": 5,
        "description": "Memory warning — triggers SERVICE_WARN rule"
    },
    "cascade": {
        "level": "ERROR",
        "service": "api-gateway",
        "messages": [
            "Upstream auth-service timeout",
            "Circuit breaker OPEN for auth-service",
            "Returning 503 to downstream clients",
        ],
        "count": 8,
        "description": "Cascade failure — multiple services affected"
    }
}

def make_entry(level: str, service: str, message: str) -> str:
    return json.dumps({
        "timestamp": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "level": level,
        "service": service,
        "message": message
    })

def write_normal(log_file: Path, count: int = 5) -> None:
    with log_file.open("a") as f:
        for _ in range(count):
            service = random.choice(SERVICES)
            msg = random.choice(NORMAL_MESSAGES).replace("{n}", str(random.randint(10, 500)))
            f.write(make_entry("INFO", service, msg) + "\n")

def inject_scenario(log_file: Path, scenario_name: str) -> None:
    scenario = ANOMALY_SCENARIOS[scenario_name]
    print(f"\n>>> INJECTING: {scenario['description']}")
    with log_file.open("a") as f:
        for i in range(scenario["count"]):
            msg = random.choice(scenario["messages"])
            f.write(make_entry(scenario["level"], scenario["service"], msg) + "\n")
            time.sleep(0.1)
    print(f">>> DONE: {scenario['count']} lines written")

def interactive_mode(log_file: Path) -> None:
    print("\nSRE Log Simulator — Interactive Mode")
    print("─────────────────────────────────────")
    print("Commands:")
    print("  n [count]  — write N normal log lines (default: 5)")
    for key, val in ANOMALY_SCENARIOS.items():
        print(f"  {key:<20} — {val['description']}")
    print("  auto       — run automatic demo sequence")
    print("  q          — quit")
    print("─────────────────────────────────────\n")

    while True:
        try:
            cmd = input("sim> ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting simulator.")
            break

        if not cmd:
            continue
        elif cmd == "q":
            break
        elif cmd.startswith("n"):
            parts = cmd.split()
            count = int(parts[1]) if len(parts) > 1 else 5
            write_normal(log_file, count)
            print(f"Wrote {count} normal log lines")
        elif cmd in ANOMALY_SCENARIOS:
            inject_scenario(log_file, cmd)
        elif cmd == "auto":
            run_auto_sequence(log_file)
        else:
            print(f"Unknown command: {cmd}")

def run_auto_sequence(log_file: Path) -> None:
    print("\n=== AUTO SEQUENCE START ===")
    steps = [
        ("normal", 10, "Baseline normal traffic"),
        ("timeout_storm", None, "Anomaly: timeout storm"),
        ("normal", 5, "Recovery: normal traffic"),
        ("memory_warn", None, "Anomaly: memory warning"),
        ("normal", 5, "Normal traffic"),
        ("disk_critical", None, "CRITICAL: disk full — requires human approval"),
        ("normal", 3, "Tail: normal traffic"),
    ]
    for kind, count, description in steps:
        print(f"\n[{description}]")
        if kind == "normal":
            write_normal(log_file, count)
            print(f"  Wrote {count} normal lines")
        else:
            inject_scenario(log_file, kind)
        time.sleep(3)
    print("\n=== AUTO SEQUENCE COMPLETE ===")
    print("Watch the agent terminal for detections.")
    print(f"Check UI: http://127.0.0.1:8001/ui/queue?api_key=dev-key")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SRE log simulator")
    parser.add_argument("--log-file", default="logs/simulated.log")
    parser.add_argument("--auto", action="store_true", help="Run auto sequence and exit")
    args = parser.parse_args()

    log_file = Path(args.log_file)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    if args.auto:
        run_auto_sequence(log_file)
    else:
        interactive_mode(log_file)
