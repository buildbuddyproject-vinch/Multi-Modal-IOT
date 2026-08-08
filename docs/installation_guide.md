# Installation Guide

## 1. Prerequisites

| Requirement | Notes |
|---|---|
| Windows 11 | Development target for this project |
| Python 3.11.x | TensorFlow 2.16 does not support 3.13+; the project's `.venv` is built against 3.11 |
| Docker Desktop | Runs MongoDB and Mosquitto locally |
| Git | Version control |

## 2. Create and Activate a Virtual Environment

PowerShell:
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

If `py -3.11` is not recognized, call the 3.11 interpreter directly, e.g.:
```powershell
& "C:\Users\<you>\AppData\Local\Programs\Python\Python311\python.exe" -m venv .venv
```

## 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

Note: `passlib`'s bcrypt backend is incompatible with `bcrypt>=4.1` (an unmaintained-upstream issue, not a project bug) — `requirements.txt` pins `bcrypt>=4.0,<4.1` specifically to avoid this; don't upgrade it independently.

## 4. Configure `.env`

```powershell
copy .env.example .env
```

Defaults work for an all-local setup. Only fill in `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` or `SMTP_*` if you actually want the alert engine to send real notifications — without them it degrades gracefully (`dispatch_status: "skipped"`), which is the expected state for local development.

## 5. Datasets

Already present at the project root, used in place (never moved into `data/`):
- `physionet/challenge-2019-1.0.0/training/{training_setA,training_setB}/*.psv`
- `mimic-iv-clinical-database-demo-2.2/`

See [`dataset_download_guide.md`](dataset_download_guide.md) if setting up on a fresh machine without them.

## 6. Local Services (MongoDB + MQTT Broker)

```powershell
# MongoDB only (required for everything from Step 7 onward):
docker compose -f deployment/docker/docker-compose.yml up -d mongo

# MongoDB + Mosquitto (required additionally for Step 11's real-time pipeline):
docker compose -f deployment/docker/docker-compose.yml --profile mqtt up -d
```
This brings up MongoDB on `localhost:27017` and (with `--profile mqtt`) Mosquitto on `localhost:1883`, both with persistent named volumes.

## 7. Run the Preprocessing + Training Pipeline (optional — pre-trained artifacts are already checked in)

Only needed if you want to reproduce the model from scratch; `models/saved/final_model.keras` and `data/processed/` already exist.
```powershell
python scripts/run_preprocessing.py
python scripts/run_eda.py
python scripts/build_model_architecture.py
python scripts/train_model.py
python scripts/run_shap_explainability.py
```

## 8. Initialize MongoDB + Provision the First Admin Account

```powershell
python scripts/init_mongodb.py
python scripts/create_admin_user.py --username admin --password "ChangeMe123!"
```
There is no self-registration endpoint by design — every account after the first is created by an admin via the frontend's Admin page (or `POST /auth/register`).

## 9. Start the Application (each in its own terminal)

```powershell
# Backend API (Swagger UI at http://localhost:8000/docs)
uvicorn src.api.main:app --reload

# Frontend (http://localhost:5173) -- first time only: cd frontend && npm install
cd frontend
npm run dev
```

Optional, for demo data / a live real-time stream:
```powershell
# Populate a handful of realistic patients using the REAL trained model + SHAP
python scripts/seed_dashboard_demo_data.py --owner-username admin --owner-password "ChangeMe123!"

# Real-time MQTT pipeline: replays real PhysioNet patients live (needs Mosquitto running)
python scripts/run_realtime_pipeline.py --owner-username admin --owner-password "ChangeMe123!"
python scripts/run_realtime_simulator.py
```

## 10. Verify Everything Is Wired Together

```powershell
python scripts/check_system_health.py
```
Reports pass/fail for MongoDB, Mosquitto, the API, and the frontend in one shot — the fastest way to confirm a fresh setup actually works end to end.

## 11. Run the Tests

```powershell
pytest tests/unit -q          # no external services required
pytest -q                     # unit + integration (integration auto-skips what isn't running)
pytest tests/e2e -q           # full-stack capstone test (needs everything from step 9 running)
```
