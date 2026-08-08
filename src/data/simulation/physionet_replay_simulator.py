"""Step 11 "hardware" simulator. Deliberately built as if it were untrusted
IoT firmware, per docs/architecture/mqtt_architecture.md §5: it imports
`src.data.schema` (the shared channel vocabulary Phase 2 firmware will also
use), `src.mqtt` (connection mechanics), and `src.config.settings` -- and
NOTHING from `src.api`, `src.database`, or `src.models`. It cannot write to
Mongo, call the API, or run the model even if it wanted to; the only thing it
knows how to do is read a PhysioNet PSV row and publish MQTT JSON. This is
what makes swapping it for real ESP32 firmware in Phase 2 a no-backend-change
operation.
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterator, Optional

import pandas as pd

from src.data.schema import CLINICAL_CHANNELS
from src.mqtt.client import build_client, connect, vitals_topic

logger = logging.getLogger(__name__)


@dataclass
class PatientStream:
    patient_id: str
    psv_path: Path
    rows: pd.DataFrame
    row_index: int = 0
    admission_time: Optional[datetime] = None

    def __post_init__(self):
        self.admission_time = datetime.now(timezone.utc)

    def next_payload(self) -> dict:
        """Advances one simulated hour and loops back to the start of the file
        once exhausted, so a demo session runs indefinitely without babysitting."""
        if self.row_index >= len(self.rows):
            self.row_index = 0
            self.admission_time = datetime.now(timezone.utc)

        row = self.rows.iloc[self.row_index]
        timestamp = self.admission_time + timedelta(hours=self.row_index)
        channels = {channel: (None if pd.isna(row[channel]) else float(row[channel])) for channel in CLINICAL_CHANNELS}
        self.row_index += 1
        return {
            "patient_id": self.patient_id,
            "timestamp": timestamp.isoformat(),
            "source": "physionet_sim",
            "channels": channels,
        }


def read_patient_psv(psv_path: Path) -> pd.DataFrame:
    return pd.read_csv(psv_path, sep="|")


def select_demo_patient_ids(raw_dir: Path, n_septic: int = 2, n_stable: int = 3, scan_limit: int = 300) -> list[str]:
    """Picks a mix of real septic and non-septic PhysioNet patients (rather than
    just the first N files) so a demo session actually shows the model catching
    a real case, not just quiet stable patients."""
    septic, stable = [], []
    files = sorted(raw_dir.glob("p*.psv"))[:scan_limit]
    for path in files:
        if len(septic) >= n_septic and len(stable) >= n_stable:
            break
        df = read_patient_psv(path)
        patient_id = path.stem
        if (df["SepsisLabel"] == 1).any() and len(septic) < n_septic:
            septic.append(patient_id)
        elif (df["SepsisLabel"] == 0).all() and len(stable) < n_stable:
            stable.append(patient_id)
    return septic + stable


def load_streams(raw_dir: Path, patient_ids: list[str]) -> list[PatientStream]:
    streams = []
    for patient_id in patient_ids:
        path = raw_dir / f"{patient_id}.psv"
        streams.append(PatientStream(patient_id, path, read_patient_psv(path)))
    return streams


def run_simulator(raw_dir: Path, patient_ids: list[str], tick_seconds: float, max_ticks: Optional[int] = None) -> None:
    streams = load_streams(raw_dir, patient_ids)
    client = build_client(client_id="physionet_replay_simulator")
    connect(client)
    client.loop_start()
    logger.info("Simulator streaming %d patients, one reading every %.1fs: %s", len(streams), tick_seconds, patient_ids)

    tick = 0
    try:
        while max_ticks is None or tick < max_ticks:
            for stream in streams:
                payload = stream.next_payload()
                client.publish(vitals_topic(stream.patient_id), _to_json(payload), qos=1)
            tick += 1
            time.sleep(tick_seconds)
    finally:
        client.loop_stop()
        client.disconnect()


def _to_json(payload: dict) -> str:
    return json.dumps(payload)
