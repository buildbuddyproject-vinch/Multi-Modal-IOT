# Multi-Modal IoT and Deep Learning Framework for Early Prediction of Sepsis in Smart ICU Environments

Final-year BE CSE project. A hybrid deep learning system (Conv1D → Bidirectional LSTM → Transformer Encoder → Dense → Sigmoid) that predicts sepsis onset risk from ICU vitals/labs time-series, served through a FastAPI backend, a MongoDB store, a real-time React dashboard with SHAP-based explainability, a Step 10 alert engine (Telegram/Email/MQTT), and a Step 11 MQTT-driven real-time ingestion pipeline that replays real PhysioNet patients as a live sensor stream.

## Project Status

**Phase 1 — Software Development: complete (Steps 1–12).** Hardware (ESP32 + real sensors) is Phase 2, not yet started. Phase 1 was built so that swapping simulated data for real IoT sensor data requires **zero changes** to the model, backend, dashboard, or database — the entire boundary is the MQTT `icu/{patient_id}/vitals` contract (see [`docs/architecture/mqtt_architecture.md`](docs/architecture/mqtt_architecture.md)). Step 11 already proves this: the "simulator" is written as if it were untrusted firmware (it cannot import `src/api`, `src/database`, or `src/models`), and the backend-side ingestion pipeline has no idea whether a reading came from that simulator or a real ESP32.

| Step | Delivered |
|---|---|
| 1 | Architecture, database design, MQTT contract, folder structure, dataset scoping |
| 2 | PhysioNet + MIMIC-IV loaders, cleaning/normalization/windowing pipeline |
| 3 | Exploratory data analysis (missingness, correlation, feature importance) |
| 4 | Hybrid CNN→BiLSTM→Transformer model architecture |
| 5 | Training pipeline (focal loss, callbacks, LR scheduling) + evaluation |
| 6 | SHAP explainability (channel-grouped Permutation explainer) |
| 7 | MongoDB (7 collections, `$jsonSchema` validators, indexes, repositories) |
| 8 | FastAPI backend (patients/vitals/predictions/alerts/SHAP CRUD) |
| 9 | React dashboard (JWT login, live monitoring, SHAP panel, dark ICU theme) |
| 10 | Alert engine (threshold + cooldown/escalation, Telegram/Email/MQTT dispatch, audit trail) |
| 11 | Real-time MQTT pipeline (untrusted-hardware-style simulator → ingestion → real model inference) |
| 12 | Full-system integration, docs finalized, end-to-end regression test |

## Datasets Used

| Dataset | Role | Location |
|---|---|---|
| PhysioNet/Computing in Cardiology Challenge 2019 | Training, validation, testing, prediction, Step 11 real-time replay | `physionet/challenge-2019-1.0.0/training/{training_setA,training_setB}` |
| MIMIC-IV Clinical Database Demo v2.2 | Schema understanding, frontend/backend testing | `mimic-iv-clinical-database-demo-2.2/` |

MIMIC-III is out of scope (not available locally).

## Model Performance (test set, `models/evaluation/metrics.json`)

| Metric | Value |
|---|---|
| AUROC | 0.766 |
| AUPRC | 0.060 |
| Best-F1 threshold | 0.207 |

**Known limitation, stated plainly:** AUPRC is low, a direct consequence of PhysioNet 2019's ~1.9% positive rate combined with a single-model (no ensembling) architecture trained on modest compute. The model is meaningfully better than random (AUROC 0.766) and its risk stratification is directionally correct (verified in Step 9/11 against both hand-authored and real patient trajectories), but it is a **research/educational artifact, not a clinically validated tool** — this is the honest caveat that belongs in the project report.

## Technology Stack

**Backend:** Python 3.11, TensorFlow 2.16 / Keras 3, FastAPI, MongoDB 7, Mosquitto (MQTT), SHAP, Pandas, NumPy, SciPy, Scikit-learn, `python-jose` + `passlib` (JWT auth), `httpx`, Docker Compose, pytest.

**Frontend:** React 19 + Vite, React Router, Axios, `react-plotly.js` (charts), plain CSS (no component framework beyond Bootstrap's base styles) -- see [`frontend/`](frontend/). A static SPA that talks to the FastAPI backend directly over JWT; no separate Node server.

## Documentation

- [System Architecture](docs/architecture/system_architecture.md)
- [Data Flow Diagram](docs/architecture/data_flow_diagram.md)
- [Database Design](docs/architecture/database_design.md)
- [MQTT Architecture](docs/architecture/mqtt_architecture.md)
- [Deployment Architecture](docs/architecture/deployment_architecture.md)
- [Project Folder Structure](PROJECT_STRUCTURE.md)
- [Installation Guide](docs/installation_guide.md) — full setup + run-book
- [Testing Strategy](docs/testing_strategy.md)

## Quick Start

Full instructions (including dataset paths, `.env` setup, and Docker) are in the [Installation Guide](docs/installation_guide.md). The short version, once `.venv` is set up and `pip install -r requirements.txt` has run:

```powershell
# 1. Start MongoDB + Mosquitto
docker compose -f deployment/docker/docker-compose.yml --profile mqtt up -d

# 2. Provision the first admin account (one-time)
python scripts/create_admin_user.py --username admin --password "ChangeMe123!"

# 3. Start the backend
uvicorn src.api.main:app --reload

# 4. In a new terminal: start the frontend (first time: cd frontend && npm install)
cd frontend
npm run dev

# 5. (optional) Populate demo patients using the real trained model
python scripts/seed_dashboard_demo_data.py --owner-username admin --owner-password "ChangeMe123!"

# 6. (optional) Start the real-time pipeline + simulator for a live MQTT stream
python scripts/run_realtime_pipeline.py --owner-username admin --owner-password "ChangeMe123!"
python scripts/run_realtime_simulator.py
```

Then open http://127.0.0.1:5173 and log in. Verify the whole stack is wired together with `python scripts/check_system_health.py`.

## Testing

```powershell
pytest -q                                    # unit + integration (integration tests skip gracefully if Docker/live servers aren't up)
pytest tests/unit -q                          # unit only, no external services required
pytest tests/e2e -q                           # capstone full-stack regression (Step 12)
```
