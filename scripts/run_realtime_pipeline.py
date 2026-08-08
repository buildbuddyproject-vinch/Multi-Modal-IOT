"""Step 11 CLI entry point: the backend-side ingestion + prediction pipeline.
Subscribes to icu/+/vitals, forwards well-formed readings to the real API,
and runs the real trained model once a patient's sliding window fills.
Requires Mosquitto and the FastAPI backend to already be running.

Usage: python scripts/run_realtime_pipeline.py --owner-username admin --owner-password "..." [--api-base-url http://127.0.0.1:8000]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import keras
import src.models.architectures.transformer_block  # noqa: F401 -- registers SinusoidalPositionalEncoding
import src.models.training.losses  # noqa: F401 -- registers BinaryFocalLoss

from src.config.settings import get_settings
from src.database.mongodb.connection import get_client, get_database, ping
from src.services.realtime_pipeline import RealtimePipeline


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--heartbeat-seconds", type=float, default=30.0)
    parser.add_argument("--owner-username", required=True,
                         help="Every patient this pipeline auto-provisions is owned by this account "
                              "(src/api/routes/patients.py's per-account privacy model).")
    parser.add_argument("--owner-password", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()

    login_resp = httpx.post(f"{args.api_base_url}/auth/login", json={"username": args.owner_username, "password": args.owner_password})
    if login_resp.status_code != 200:
        print(f"Could not authenticate as '{args.owner_username}': {login_resp.text}")
        sys.exit(1)
    owner_token = login_resp.json()["access_token"]

    client = get_client()
    if not ping(client):
        print("Could not reach MongoDB. Start it with: docker compose -f deployment/docker/docker-compose.yml up -d mongo")
        sys.exit(1)
    db = get_database(client)

    model_path = settings.resolve_path("./models") / "saved" / "final_model.keras"
    print(f"Loading trained model from {model_path}")
    model = keras.models.load_model(model_path, compile=False)

    metadata_path = settings.processed_dir / "physionet2019" / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    mean, std, medians = metadata["scaler"]["mean"], metadata["scaler"]["std"], metadata["train_medians"]

    pipeline = RealtimePipeline(db, model, mean, std, medians, args.api_base_url, owner_token=owner_token)
    print(f"Ingestion + prediction pipeline listening on icu/+/vitals via {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
    try:
        pipeline.run(heartbeat_seconds=args.heartbeat_seconds)
    except KeyboardInterrupt:
        pass
    finally:
        pipeline.close()


if __name__ == "__main__":
    main()
