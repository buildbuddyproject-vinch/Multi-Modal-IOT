"""Step 12 CLI entry point: one-shot health check across the whole stack --
MongoDB, Mosquitto, the FastAPI backend, the React frontend, and the trained
model artifacts on disk. Exits non-zero if anything required is down, so it
doubles as a quick post-setup verification and a pre-demo sanity check.

Usage: python scripts/check_system_health.py [--api-base-url ...] [--frontend-base-url ...]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import paho.mqtt.publish as mqtt_publish

from src.config.settings import get_settings
from src.database.mongodb.connection import get_client, ping


def check_mongodb() -> tuple[bool, str]:
    try:
        client = get_client()
        return (True, "reachable") if ping(client) else (False, "ping failed")
    except Exception as exc:
        return False, str(exc)


def check_mosquitto() -> tuple[bool, str]:
    settings = get_settings()
    try:
        mqtt_publish.single(
            "system/health_check", payload="{}",
            hostname=settings.mqtt_broker_host, port=settings.mqtt_broker_port, keepalive=3,
        )
        return True, f"reachable at {settings.mqtt_broker_host}:{settings.mqtt_broker_port}"
    except Exception as exc:
        return False, str(exc)


def check_http(url: str, label: str) -> tuple[bool, str]:
    try:
        resp = httpx.get(url, timeout=3.0)
        return (resp.status_code == 200), f"HTTP {resp.status_code} from {url}"
    except Exception as exc:
        return False, f"{label} unreachable: {exc}"


def check_model_artifacts() -> tuple[bool, str]:
    settings = get_settings()
    model_path = settings.resolve_path("./models") / "saved" / "final_model.keras"
    metadata_path = settings.processed_dir / "physionet2019" / "metadata.json"
    missing = [str(p) for p in (model_path, metadata_path) if not p.exists()]
    return (not missing), ("present" if not missing else f"missing: {missing}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--frontend-base-url", default="http://127.0.0.1:5173")
    args = parser.parse_args()

    checks = [
        ("MongoDB", check_mongodb, True),
        ("Mosquitto (MQTT broker)", check_mosquitto, False),
        ("FastAPI backend", lambda: check_http(f"{args.api_base_url}/health", "API"), True),
        ("React frontend", lambda: check_http(f"{args.frontend_base_url}/", "Frontend"), False),
        ("Trained model + scaler artifacts", check_model_artifacts, True),
    ]

    print(f"{'Component':<35}{'Status':<8}Detail")
    print("-" * 80)
    all_required_ok = True
    for name, check_fn, required in checks:
        ok, detail = check_fn()
        status = "OK" if ok else "FAIL"
        marker = "" if (ok or not required) else "  (required)"
        print(f"{name:<35}{status:<8}{detail}{marker}")
        if required and not ok:
            all_required_ok = False

    print("-" * 80)
    if all_required_ok:
        print("All required components are healthy. Optional components (MQTT, frontend) may still need starting.")
    else:
        print("One or more REQUIRED components are down -- see above.")
    sys.exit(0 if all_required_ok else 1)


if __name__ == "__main__":
    main()
