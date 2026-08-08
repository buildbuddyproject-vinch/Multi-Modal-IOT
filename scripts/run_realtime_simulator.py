"""Step 11 CLI entry point: the untrusted-hardware-style MQTT publisher.
Replays real PhysioNet patients (a mix of septic and stable cases) as a live
icu/{patient_id}/vitals stream, one simulated hour per tick. Requires Mosquitto
running: docker compose -f deployment/docker/docker-compose.yml --profile mqtt up -d mosquitto

Usage: python scripts/run_realtime_simulator.py [--tick-seconds 5] [--patient-ids p000001 p000045 ...]
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config.settings import get_settings
from src.data.simulation.physionet_replay_simulator import run_simulator, select_demo_patient_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tick-seconds", type=float, default=5.0)
    parser.add_argument("--patient-ids", nargs="*", default=None, help="defaults to an auto-selected septic+stable mix")
    parser.add_argument("--max-ticks", type=int, default=None, help="stop after N ticks (default: run forever)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    raw_dir = get_settings().physionet_dir / "training_setA"

    patient_ids = args.patient_ids or select_demo_patient_ids(raw_dir)
    print(f"Streaming {len(patient_ids)} patients from {raw_dir}: {patient_ids}")
    run_simulator(raw_dir, patient_ids, tick_seconds=args.tick_seconds, max_ticks=args.max_ticks)


if __name__ == "__main__":
    main()
