"""Step 9 CLI entry point: seed realistic demo patients through the REAL FastAPI
backend (not direct DB writes) so the dashboard has something to show. This is
"simulated data" in the same sense the rest of Phase 1 is -- hand-authored
clinical trajectories -- but every prediction is produced by the ACTUAL trained
model (models/saved/final_model.keras) and every SHAP explanation by the ACTUAL
Step 6 explainer, not fabricated numbers. Step 11 replaces the hand-authored
trajectories with a continuous MQTT-driven simulator; nothing downstream of the
API changes.

Usage: python scripts/seed_dashboard_demo_data.py --owner-username admin --owner-password "..." [--api-base-url http://127.0.0.1:8000]
"""
import argparse
import json
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
import numpy as np

import keras
import src.models.architectures.transformer_block  # noqa: F401 -- registers SinusoidalPositionalEncoding
import src.models.training.losses  # noqa: F401 -- registers BinaryFocalLoss

from src.config.settings import get_settings
from src.data.schema import CLINICAL_CHANNELS
from src.models.explainability.patient_report import build_patient_explanation
from src.models.explainability.shap_explainer import build_explainer, compute_shap_values

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

WINDOW_SIZE = 8
HOURS = 30

# Approximate direction + relative magnitude (in std units) that sepsis severity
# moves each channel. Channels absent here stay at their train-set median plus
# small noise -- clinically that means "not part of the sepsis picture for this
# demo", which is true for most of the 34 channels.
CHANNEL_SEVERITY_SENSITIVITY: dict[str, float] = {
    "HR": 2.5, "Resp": 2.0, "Temp": 1.8, "WBC": 2.0, "Lactate": 3.0,
    "SBP": -2.0, "MAP": -2.2, "DBP": -1.2, "O2Sat": -1.5, "SaO2": -1.2,
    "Platelets": -1.2, "Creatinine": 1.3, "BUN": 1.1, "BaseExcess": -1.3,
    "HCO3": -1.0, "pH": -0.8, "PaCO2": 0.5, "FiO2": 0.6, "Bilirubin_total": 0.6,
    "TroponinI": 0.4, "Fibrinogen": -0.4, "PTT": 0.5, "Glucose": 0.5,
}


@dataclass
class DemoPatient:
    patient_id: str
    age: float
    sex: str
    unit_admitted: str
    severity_fn: Callable[[np.ndarray], np.ndarray]  # hour index array -> severity in [0, 1]
    noise_scale: float = 0.25  # fraction of a channel's std used as per-hour noise
    seed: int = 0


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def severity_stable(hours: np.ndarray) -> np.ndarray:
    return np.full_like(hours, 0.05, dtype=float)


def severity_mild(hours: np.ndarray) -> np.ndarray:
    return np.full_like(hours, 0.30, dtype=float)


def severity_gradual_onset(hours: np.ndarray) -> np.ndarray:
    return 0.05 + 0.90 * _sigmoid((hours - HOURS * 0.6) / 3.0)


def severity_acute_late_onset(hours: np.ndarray) -> np.ndarray:
    return 0.05 + 0.90 * _sigmoid((hours - HOURS * 0.85) / 1.2)


def severity_recovering(hours: np.ndarray) -> np.ndarray:
    return 0.10 + 0.75 * _sigmoid(-(hours - HOURS * 0.35) / 3.0)


def severity_septic_shock_unstable(hours: np.ndarray) -> np.ndarray:
    ramp = 0.15 + 0.75 * _sigmoid((hours - HOURS * 0.35) / 4.0)
    oscillation = 0.08 * np.sin(hours / 1.5)
    return np.clip(ramp + oscillation, 0.05, 0.98)


DEMO_PATIENTS = [
    DemoPatient("demo_p01_stable", age=54, sex="F", unit_admitted="MICU", severity_fn=severity_stable, seed=1),
    DemoPatient("demo_p02_gradual_sepsis", age=71, sex="M", unit_admitted="SICU", severity_fn=severity_gradual_onset, seed=2),
    DemoPatient("demo_p03_acute_deterioration", age=63, sex="M", unit_admitted="MICU", severity_fn=severity_acute_late_onset, seed=3),
    DemoPatient("demo_p04_mild_risk", age=68, sex="F", unit_admitted="CCU", severity_fn=severity_mild, seed=4),
    DemoPatient("demo_p05_recovering", age=47, sex="M", unit_admitted="SICU", severity_fn=severity_recovering, seed=5),
    DemoPatient("demo_p06_septic_shock", age=76, sex="F", unit_admitted="MICU", severity_fn=severity_septic_shock_unstable, seed=6),
]


def load_scaler_and_baseline() -> tuple[dict, dict, dict]:
    settings = get_settings()
    metadata_path = settings.processed_dir / "physionet2019" / "metadata.json"
    with open(metadata_path) as f:
        metadata = json.load(f)
    return metadata["scaler"]["mean"], metadata["scaler"]["std"], metadata["train_medians"]


def generate_raw_trajectory(patient: DemoPatient, mean: dict, std: dict, baseline: dict) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(patient.seed)
    hours = np.arange(HOURS)
    severity = patient.severity_fn(hours)

    trajectory = {}
    for channel in CLINICAL_CHANNELS:
        base = baseline.get(channel, mean[channel])
        sensitivity = CHANNEL_SEVERITY_SENSITIVITY.get(channel, 0.0)
        drift = sensitivity * severity * std[channel]
        noise = rng.normal(0.0, patient.noise_scale * std[channel], size=HOURS)
        trajectory[channel] = base + drift + noise
    return trajectory


def normalize_window(window_raw: np.ndarray, channels: list[str], mean: dict, std: dict) -> np.ndarray:
    mean_vec = np.array([mean[c] for c in channels])
    std_vec = np.array([std[c] for c in channels])
    return (window_raw - mean_vec) / std_vec


def run_patient(client: httpx.Client, model, patient: DemoPatient, mean: dict, std: dict, baseline: dict, background: np.ndarray) -> None:
    logger.info("Seeding patient %s (%s)", patient.patient_id, patient.severity_fn.__name__)
    trajectory = generate_raw_trajectory(patient, mean, std, baseline)
    raw_matrix = np.stack([trajectory[c] for c in CLINICAL_CHANNELS], axis=1)  # (HOURS, n_channels)

    start_time = datetime.now(timezone.utc) - timedelta(hours=HOURS)
    resp = client.post("/patients", json={
        "patient_id": patient.patient_id, "source_dataset": "live", "age": patient.age,
        "sex": patient.sex, "unit_admitted": patient.unit_admitted,
        "admission_time": start_time.isoformat(), "current_status": "active",
    })
    if resp.status_code not in (201, 409):
        resp.raise_for_status()

    last_prediction_id, last_probability = None, None
    for hour in range(HOURS):
        timestamp = start_time + timedelta(hours=hour)
        channels = {c: float(raw_matrix[hour, i]) for i, c in enumerate(CLINICAL_CHANNELS)}
        resp = client.post("/vitals", json={
            "patient_id": patient.patient_id, "timestamp": timestamp.isoformat(),
            "source": "physionet_sim", "channels": channels, "ingest_seq": hour,
        })
        resp.raise_for_status()

        if hour < WINDOW_SIZE - 1:
            continue

        window_raw = raw_matrix[hour - WINDOW_SIZE + 1: hour + 1]
        window_norm = normalize_window(window_raw, CLINICAL_CHANNELS, mean, std).astype(np.float32)
        probability = float(model(window_norm[None, ...], training=False).numpy()[0, 0])

        # predicted_label/risk_level are NOT sent -- the server derives them
        # authoritatively from sepsis_probability (src/models/inference/risk.py)
        # and, as of Step 10, automatically runs every prediction through the
        # alert engine (threshold + cooldown + Telegram/email dispatch), so no
        # separate POST /alerts call is needed here anymore.
        resp = client.post("/predictions", json={
            "patient_id": patient.patient_id, "sepsis_probability": probability,
            "model_version": "hybrid_cnn_bilstm_transformer_v1",
            "window_start": (timestamp - timedelta(hours=WINDOW_SIZE - 1)).isoformat(),
            "window_end": timestamp.isoformat(),
        })
        resp.raise_for_status()
        prediction = resp.json()
        last_prediction_id, last_probability, last_risk_level = prediction["id"], probability, prediction["risk_level"]
        last_window_norm = window_norm

    logger.info("  final probability=%.3f risk=%s", last_probability, last_risk_level)

    logger.info("  computing SHAP explanation for latest prediction...")
    explainer = build_explainer(model, background, WINDOW_SIZE, len(CLINICAL_CHANNELS), channel_names=CLINICAL_CHANNELS)
    shap_result = compute_shap_values(explainer, last_window_norm[None, ...], max_evals=150)
    explanation = build_patient_explanation(shap_result, index=0, prediction_probability=last_probability)
    resp = client.post("/shap", json={
        "prediction_id": last_prediction_id, "patient_id": patient.patient_id,
        "shap_values": explanation["shap_values"], "shap_plot_type": "waterfall",
        "top_contributing_features": explanation["top_contributing_features"],
    })
    resp.raise_for_status()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--n-background", type=int, default=30, help="background sample size for SHAP")
    parser.add_argument("--owner-username", required=True,
                         help="Every demo patient is owned by this account (src/api/routes/patients.py's per-account privacy model).")
    parser.add_argument("--owner-password", required=True)
    args = parser.parse_args()

    settings = get_settings()
    model_path = settings.resolve_path("./models") / "saved" / "final_model.keras"
    logger.info("Loading trained model from %s", model_path)
    model = keras.models.load_model(model_path, compile=False)

    mean, std, baseline = load_scaler_and_baseline()

    processed_dir = settings.processed_dir / "physionet2019"
    with np.load(processed_dir / "train.npz") as data:
        X_train = data["X"]
    rng = np.random.default_rng(42)
    background = X_train[rng.choice(len(X_train), args.n_background, replace=False)]

    with httpx.Client(base_url=args.api_base_url, timeout=30.0) as anon_client:
        resp = anon_client.get("/health")
        resp.raise_for_status()
        if not resp.json()["mongo_connected"]:
            print("API is reachable but reports MongoDB is not connected. Aborting.")
            sys.exit(1)

        login_resp = anon_client.post("/auth/login", json={"username": args.owner_username, "password": args.owner_password})
        if login_resp.status_code != 200:
            print(f"Could not authenticate as '{args.owner_username}': {login_resp.text}")
            sys.exit(1)
        owner_token = login_resp.json()["access_token"]

    with httpx.Client(base_url=args.api_base_url, timeout=30.0, headers={"Authorization": f"Bearer {owner_token}"}) as client:
        for patient in DEMO_PATIENTS:
            run_patient(client, model, patient, mean, std, baseline, background)

    print(f"\nSeeded {len(DEMO_PATIENTS)} demo patients ({HOURS}h of vitals/predictions each) via {args.api_base_url}")


if __name__ == "__main__":
    main()
