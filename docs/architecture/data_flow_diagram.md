# Data Flow Diagram

## 1. End-to-End Flow (Phase 1, simulated source)

```mermaid
sequenceDiagram
    participant PSV as PhysioNet PSV File
    participant SIM as Simulator (Step 11)
    participant MQTT as MQTT Broker
    participant ING as Ingestion Service
    participant DB as MongoDB
    participant FE as Feature Engineering
    participant MODEL as Hybrid DL Model
    participant SHAP as SHAP Service
    participant ALERT as Alert Engine
    participant API as FastAPI
    participant DASH as Dash Dashboard
    participant NOTIFY as Telegram / Email

    PSV->>SIM: read next row (configurable interval, e.g. 5s)
    SIM->>MQTT: publish icu/{patient_id}/vitals (JSON)
    MQTT->>ING: deliver message
    ING->>ING: validate schema + normalize units
    ING->>DB: insert into vitals collection
    ING->>FE: forward reading for windowing
    FE->>FE: append to rolling window (per patient_id)
    alt window has enough timesteps
        FE->>MODEL: feature tensor [timesteps, channels]
        MODEL->>MODEL: CNN -> BiLSTM -> Transformer -> Dense -> Sigmoid
        MODEL->>DB: insert into predictions collection
        MODEL->>SHAP: request explanation (async/on-demand)
        SHAP->>DB: insert into prediction_history (shap artifacts)
        MODEL->>ALERT: risk_probability
        ALERT->>ALERT: map probability -> Low/Medium/High/Critical
        ALERT->>DB: insert into alerts + audit_logs
        ALERT->>NOTIFY: dispatch if threshold >= Medium
    end
    DASH->>API: poll GET /predictions/latest, /alerts, /vitals
    API->>DB: query
    API-->>DASH: JSON response
    DASH->>DASH: render charts, SHAP plots, alert banners
```

## 2. Preprocessing Data Flow (Step 2, offline/batch)

```mermaid
flowchart LR
    RAW1["MIMIC-IV Demo CSVs\n(hosp/, icu/)"] --> CLEAN1["Cleaning +\nSchema Mapping"]
    RAW2["PhysioNet 2019 PSV\n(training_setA, training_setB)"] --> CLEAN2["Cleaning +\nMissing Value Handling"]

    CLEAN1 --> ALIGN["Feature Alignment\n(common vitals/labs schema)"]
    CLEAN2 --> ALIGN

    ALIGN --> NORM["Normalization\n(z-score / min-max, fit on train only)"]
    NORM --> WIN["Sliding Window\nGeneration (per patient, per timestep)"]
    WIN --> SPLIT["Train / Validation / Test\nSplit (patient-level, stratified by SepsisLabel)"]
    SPLIT --> SAVE["Save processed arrays\ndata/processed/*.npz + metadata.json"]
```

## 3. Data Origin Traceability

Every document inserted into `vitals` carries a `source` field: `"physionet_sim"`, `"mimic_replay"`, or (Phase 2) `"iot_sensor"`. This field is metadata only — used for filtering/auditing in the dashboard's "Data Source" badge — and **never** used to branch ingestion, feature engineering, model, or alert logic. This is what enables the Phase 2 hardware swap to be additive rather than a rewrite.
