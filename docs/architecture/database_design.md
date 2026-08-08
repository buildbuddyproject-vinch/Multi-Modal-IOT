# MongoDB Database Design

Database name: `sepsis_icu` (configurable via `.env` → `MONGO_DB_NAME`)

## 1. Collections Overview

| Collection | Purpose | Written by | Read by |
|---|---|---|---|
| `patients` | Patient demographics + admission metadata | Ingestion / Admin API | API, Dashboard |
| `vitals` | Raw time-series vitals/lab readings (source-agnostic) | Ingestion Service | Feature Engineering, API, Dashboard |
| `predictions` | Model output per inference window | Prediction Service | API, Dashboard, Alert Engine |
| `prediction_history` | SHAP artifacts + versioned prediction snapshots for trend charts | SHAP Service | API, Dashboard |
| `alerts` | Generated alerts with risk level + dispatch status | Alert Engine | API, Dashboard |
| `audit_logs` | System + user action trail (predictions run, alerts dispatched, config changes, login events) | All services | Admin API |
| `users` | Dashboard authentication (clinician/admin roles) | Admin API | Auth middleware |
| `devices` (Phase 2, schema reserved now) | IoT device/sensor registry (ESP32 MAC, patient binding, last-seen) | Not written in Phase 1 | Reserved |

## 2. Schema Definitions

### 2.1 `patients`
```json
{
  "_id": "ObjectId",
  "patient_id": "string (unique, e.g. p000001 for PhysioNet or subject_id for MIMIC)",
  "source_dataset": "physionet_2019 | mimic_iv_demo | live",
  "age": "number",
  "sex": "M | F",
  "unit_admitted": "string (ICU unit label)",
  "admission_time": "ISODate",
  "current_status": "active | discharged | deceased",
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```
Indexes: unique on `patient_id`; index on `current_status`.

### 2.2 `vitals`
```json
{
  "_id": "ObjectId",
  "patient_id": "string",
  "timestamp": "ISODate",
  "source": "physionet_sim | mimic_replay | iot_sensor",
  "channels": {
    "HR": "number|null", "O2Sat": "number|null", "Temp": "number|null",
    "SBP": "number|null", "DBP": "number|null", "MAP": "number|null",
    "Resp": "number|null", "EtCO2": "number|null",
    "BaseExcess": "number|null", "HCO3": "number|null", "FiO2": "number|null",
    "pH": "number|null", "PaCO2": "number|null", "SaO2": "number|null",
    "Glucose": "number|null", "Lactate": "number|null", "WBC": "number|null",
    "Platelets": "number|null", "Creatinine": "number|null"
  },
  "ingest_seq": "number (monotonic per patient, for window ordering)",
  "created_at": "ISODate"
}
```
Indexes: compound `(patient_id, timestamp)`; compound `(patient_id, ingest_seq)`.
Note: `channels` uses the PhysioNet 2019 feature set as the canonical schema since it is the training/validation source; MIMIC-IV Demo fields are mapped onto this schema at ingestion (see `data_flow_diagram.md` §2).

### 2.3 `predictions`
```json
{
  "_id": "ObjectId",
  "patient_id": "string",
  "window_start": "ISODate",
  "window_end": "ISODate",
  "sepsis_probability": "number (0-1)",
  "predicted_label": "0 | 1",
  "model_version": "string (e.g. hybrid_cnn_bilstm_transformer_v1)",
  "risk_level": "Low | Medium | High | Critical",
  "inference_latency_ms": "number",
  "created_at": "ISODate"
}
```
Indexes: compound `(patient_id, created_at)` descending, for "latest prediction" queries.

### 2.4 `prediction_history`
```json
{
  "_id": "ObjectId",
  "prediction_id": "ObjectId (ref predictions._id)",
  "patient_id": "string",
  "shap_values": "object (feature -> contribution)",
  "shap_plot_type": "summary | waterfall | force",
  "top_contributing_features": ["array of {feature, value, contribution}"],
  "explanation_method": "shap | lime",
  "created_at": "ISODate"
}
```
Indexes: index on `patient_id`; index on `prediction_id`.

### 2.5 `alerts`
```json
{
  "_id": "ObjectId",
  "patient_id": "string",
  "prediction_id": "ObjectId (ref predictions._id)",
  "risk_level": "Low | Medium | High | Critical",
  "message": "string",
  "channels_dispatched": ["dashboard", "telegram", "email"],
  "dispatch_status": {"telegram": "sent|failed|skipped", "email": "sent|failed|skipped"},
  "acknowledged": "boolean",
  "acknowledged_by": "string|null",
  "acknowledged_at": "ISODate|null",
  "created_at": "ISODate"
}
```
Indexes: compound `(patient_id, created_at)`; index on `risk_level`; index on `acknowledged`.

### 2.6 `audit_logs`
```json
{
  "_id": "ObjectId",
  "actor": "string (system | user_id)",
  "action": "string (e.g. prediction_run, alert_dispatched, login, config_change)",
  "target_type": "string (patient | prediction | alert | user)",
  "target_id": "string",
  "details": "object (free-form)",
  "timestamp": "ISODate"
}
```
Indexes: index on `timestamp` descending; index on `action`.

### 2.7 `users`
```json
{
  "_id": "ObjectId",
  "username": "string (unique)",
  "hashed_password": "string (bcrypt)",
  "role": "admin | clinician",
  "created_at": "ISODate",
  "last_login": "ISODate|null"
}
```
Indexes: unique on `username`.

### 2.8 `devices` (Phase 2 — schema reserved, not implemented in Phase 1)
```json
{
  "_id": "ObjectId",
  "device_id": "string (ESP32 MAC or UUID)",
  "patient_id": "string|null",
  "sensor_types": ["array e.g. MAX30100(HR/SpO2), DS18B20(Temp)"],
  "last_seen": "ISODate",
  "status": "online | offline"
}
```

## 3. Data Retention & Volume Notes

- `vitals` is the highest-volume collection; TTL indexing is **not** applied in Phase 1 (academic project needs full history), but the schema is TTL-index-ready (`created_at`) for future production use.
- `prediction_history` SHAP payloads can be large (per-feature arrays); stored as compact objects, not full SHAP explainer pickles.
