# MQTT Architecture (Hardware-Ready)

MQTT is the **swap boundary** between Phase 1 (simulated data) and Phase 2 (ESP32 + real sensors). Both phases publish to the identical topic/payload contract defined here; only the publisher process changes.

## 1. Broker

- Local development: **Eclipse Mosquitto** running via Docker (`deployment/docker/mosquitto/`) or a local Windows install.
- Config surface: `MQTT_BROKER_HOST`, `MQTT_BROKER_PORT` (default 1883), `MQTT_USERNAME`, `MQTT_PASSWORD` (optional in dev) — all via `.env`.

## 2. Topic Design

| Topic | Direction | Publisher (Phase 1) | Publisher (Phase 2) | Payload |
|---|---|---|---|---|
| `icu/{patient_id}/vitals` | Device → Backend | Simulator (`src/data/simulation`) | ESP32 gateway | JSON vitals reading (see §3) |
| `icu/{patient_id}/status` | Device → Backend | Simulator | ESP32 gateway | `{"status": "online\|offline", "battery": number, "timestamp": ISO8601}` |
| `icu/{patient_id}/prediction` | Backend → Dashboard | Prediction Service | Prediction Service (unchanged) | `{"sepsis_probability": number, "risk_level": string, "timestamp": ISO8601}` |
| `icu/{patient_id}/alert` | Backend → Dashboard | Alert Engine | Alert Engine (unchanged) | `{"risk_level": string, "message": string, "timestamp": ISO8601}` |
| `system/heartbeat` | Bi-directional | Ingestion Service | Ingestion Service (unchanged) | `{"service": string, "status": "alive", "timestamp": ISO8601}` |

QoS: 1 (at-least-once) for `vitals` and `alert` topics — a missed vital reading or alert is unacceptable; QoS 0 for `status`/`heartbeat`.

## 3. `icu/{patient_id}/vitals` Payload Contract

```json
{
  "patient_id": "p000001",
  "timestamp": "2026-08-05T10:15:30Z",
  "source": "physionet_sim",
  "channels": {
    "HR": 88.0, "O2Sat": 97.0, "Temp": 37.1,
    "SBP": 118.0, "DBP": 76.0, "MAP": 90.0,
    "Resp": 18.0, "Glucose": 110.0, "Lactate": 1.4
  }
}
```

Rules the ingestion service enforces regardless of publisher identity:
1. `patient_id` and `timestamp` are required; message is rejected (logged to `audit_logs`) if missing.
2. `channels` values are `number | null` only — never strings; unavailable sensor channels are `null`, not omitted (keeps schema stable for the feature engineering step).
3. `source` must be one of the enumerated values in `database_design.md §2.2`. Phase 2 firmware will send `"iot_sensor"`.
4. Payload size capped at 4 KB (single-timestep readings are tiny; this guards against malformed bursts).

## 4. Why MQTT Instead of Direct API Calls for Ingestion

- Decouples publisher liveness from backend liveness (broker buffers briefly if the backend restarts).
- Identical pub/sub contract works whether the publisher is a Python simulator process or ESP32 firmware — no HTTP client needed on the microcontroller, which is a natural fit for constrained IoT devices (Phase 2).
- Supports multiple concurrent patient streams without the ingestion service polling anything.

## 5. Phase 1 Simulator's Role

The Step 11 simulator is simply the **first implementation of an MQTT publisher** against this contract. It is intentionally built as if it were untrusted hardware: it does not import from `src/api`, `src/database`, or `src/models` — it only knows how to read a PhysioNet PSV row and publish MQTT JSON. This is what guarantees Phase 2 (ESP32) is a drop-in replacement.

## 6. Phase 2 Preview (not built in Phase 1)

ESP32 firmware will run a lightweight MQTT client (e.g. `PubSubClient` library), read from MAX30100 (HR/SpO2), DS18B20 (Temp), and a respiration/BP module, batch into the same JSON contract, and publish to `icu/{patient_id}/vitals` on the same broker. No backend code changes are required — this is validated in Step 11 by pointing the dashboard/API at simulator-published topics and confirming the pipeline is publisher-agnostic.
