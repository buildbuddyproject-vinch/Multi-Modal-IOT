# Project Folder Structure

This reflects the structure as actually built (Steps 1–12), not the original Step 1 plan — see the note at the bottom for the handful of deliberate deviations.

```
Multi-modal IOT/
├── README.md
├── PROJECT_STRUCTURE.md
├── requirements.txt
├── .env.example
│
├── docs/
│   ├── architecture/
│   │   ├── system_architecture.md
│   │   ├── data_flow_diagram.md
│   │   ├── database_design.md
│   │   ├── mqtt_architecture.md
│   │   └── deployment_architecture.md
│   ├── installation_guide.md
│   ├── dataset_download_guide.md
│   └── testing_strategy.md
│
├── mimic-iv-clinical-database-demo-2.2/   # raw dataset (already present, untouched)
├── physionet/                             # raw dataset (already present, untouched)
│   └── challenge-2019-1.0.0/training/{training_setA,training_setB}/*.psv
│
├── data/processed/
│   ├── physionet2019/                # windowed .npz + metadata.json (scaler stats, Step 2)
│   └── mimic_iv/                     # cleaned/mapped tables (Step 2)
│
├── notebooks/eda/outputs/            # Step 3 EDA plots + summary report
│
├── src/
│   ├── config/                       # Pydantic settings (src/config/settings.py)
│   ├── data/
│   │   ├── loaders/                  # MIMIC-IV / PhysioNet loaders (Step 2)
│   │   ├── preprocessing/            # cleaning, normalization, windowing, split (Step 2)
│   │   └── simulation/               # Step 11 untrusted-hardware-style MQTT publisher
│   ├── eda/                          # Step 3 statistics/plots modules
│   ├── models/
│   │   ├── architectures/            # CNN, BiLSTM, Transformer, hybrid model (Step 4)
│   │   ├── training/                 # losses, callbacks, train loop (Step 5)
│   │   ├── evaluation/               # metrics, plots (Step 5)
│   │   ├── explainability/           # SHAP explainer, plots, patient report (Step 6)
│   │   └── inference/                # risk.py: probability -> predicted_label/risk_level (Step 9/10)
│   ├── database/mongodb/             # connection, schemas, indexes, bootstrap, repositories (Step 7)
│   ├── api/
│   │   ├── routes/                   # health, auth, patients, vitals, predictions, alerts, shap, audit
│   │   ├── schemas/                  # Pydantic request/response models
│   │   ├── services/                 # reserved for future route business logic (unused so far --
│   │   │                             #   routes stayed simple enough not to need it)
│   │   ├── dependencies.py           # FastAPI DI: db, repos, auth, alert engine
│   │   ├── security.py               # JWT + password hashing (Step 9)
│   │   └── main.py                   # app assembly
│   ├── mqtt/                         # client.py: shared paho-mqtt connection helpers (Step 11)
│   ├── alerts/
│   │   ├── alert_engine.py           # threshold/cooldown/escalation decision (Step 10)
│   │   └── dispatchers/              # telegram, email, mqtt (Step 10/11)
│   ├── services/
│   │   └── realtime_pipeline.py      # standalone Ingestion+Prediction Service (Step 11) --
│   │                                 #   NOT invoked by FastAPI routes, so it lives outside src/api
│   └── utils/                        # logging_config.py
│
├── dashboard/
│   ├── assets/                       # dark_icu_theme.css
│   ├── pages/                        # login, home, patients, patient_detail, live_monitoring, alerts, admin
│   ├── components/                   # navbar, cards (reusable Dash components)
│   ├── utils/                        # formatting.py: pure, unit-testable chart/table builders
│   ├── api_client.py                 # httpx client -- the dashboard's ONLY path to data
│   ├── auth.py                       # Flask-session helpers
│   ├── config.py                     # dashboard-side settings
│   ├── theme.py                      # Plotly dark ICU template + risk colors
│   └── app.py                        # Dash app assembly, routing guard
│
├── models/
│   ├── checkpoints/                  # ModelCheckpoint outputs during training
│   ├── saved/                        # final_model.keras + architecture/ snapshot
│   ├── evaluation/                   # metrics.json, ROC/confusion-matrix plots
│   ├── explainability/               # SHAP summary/waterfall/force plots, patient_explanations.json
│   └── logs/                         # TensorBoard event files
│
├── tests/
│   ├── unit/                         # mongomock / httpx.MockTransport / no external services
│   ├── integration/                  # real Docker Mongo + Mosquitto + live servers, skip gracefully if down
│   └── e2e/                          # Step 12 capstone: the full stack, start to finish
│
├── scripts/                          # CLI entry points (see docs/installation_guide.md for the full list)
├── logs/                             # runtime application logs (git-ignored)
└── deployment/
    └── docker/
        ├── docker-compose.yml        # mongo (always-on) + mosquitto (behind the `mqtt` profile)
        └── mosquitto/config/mosquitto.conf
```

**Design rule enforced by this structure:** `src/models`, `src/api`, `src/database`, and `dashboard/` never import from `src/data/simulation`. The simulator is a peer of future Phase 2 hardware, not a dependency of the core system (see [`docs/architecture/mqtt_architecture.md`](docs/architecture/mqtt_architecture.md)).

**Deviations from the original Step 1 plan**, made deliberately during later steps and left here rather than silently reconciled:
- `src/services/realtime_pipeline.py` is a new top-level package, not `src/api/services/` — it's a standalone long-running daemon (MQTT subscriber), never invoked by a FastAPI route, so it doesn't belong under `src/api/`.
- `dashboard/callbacks/` was planned as a separate module; in practice each page's callbacks live directly in that page's file (`dashboard/pages/*.py`) — standard Dash Pages convention, and there was never enough callback logic per page to justify splitting it out.
- No `src/alerts/worker.py` — alert dispatch runs in-process inside the `POST /predictions` request (see `docs/architecture/deployment_architecture.md` §1) rather than as a separate MQTT-subscribing worker.
