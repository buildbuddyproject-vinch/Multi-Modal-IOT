# Testing Strategy

## 1. Principles

- Every step (2 through 12) ships with tests before being marked complete — nothing is "tested manually only."
- Tests must run without live external services where feasible: MongoDB is mocked with `mongomock` for unit tests; a real MongoDB (via Docker) is used only for `tests/integration`.
- No test depends on network access to PhysioNet/MIMIC servers — datasets are already local.

## 2. Test Layers

| Layer | Location | Scope | Runs against |
|---|---|---|---|
| Unit | `tests/unit/` | Single function/class: preprocessing transforms, model layer shapes, alert threshold logic, SHAP formatting, MQTT payload validation | Mocks only (`mongomock`, in-memory MQTT loopback, tiny synthetic tensors) |
| Integration | `tests/integration/` | Cross-component: ingestion → MongoDB write → feature window build; FastAPI route → real Mongo (Docker) → response schema | Dockerized MongoDB/Mosquitto |
| End-to-End | `tests/e2e/` | Full pipeline: simulator publishes → prediction stored → alert dispatched → dashboard API reflects it | Full local stack (Step 12) |

## 3. Per-Step Testing Checklist

| Step | What gets tested |
|---|---|
| 2 (Dataset) | Loader returns expected row/column counts; missing-value strategy leaves no NaNs in required channels; window shapes match `(timesteps, n_channels)`; split has no patient leakage across train/val/test |
| 3 (EDA) | Notebook/script executes end-to-end without error; generated plot files exist on disk |
| 4 (Model architecture) | Model builds without error; `model.summary()` output shape matches expected `(batch, 1)`; forward pass on random tensor produces values in `[0,1]` |
| 5 (Training) | Training runs for 1-2 epochs on a small subset without NaN loss; checkpoint file is written; evaluation metrics (AUROC, AUPRC, F1, precision, recall, specificity, sensitivity) computed and within valid ranges [0,1] |
| 6 (XAI) | SHAP values sum consistency check (approx. matches model output delta from base value); plots saved as files and are non-empty |
| 7 (MongoDB) | CRUD round-trip for every collection; unique index constraints enforced; connection failure handled gracefully |
| 8 (FastAPI) | Each endpoint has a `TestClient` test for 200 path and at least one error path (404/422); Swagger schema loads (`/docs`, `/openapi.json`) |
| 9 (Dashboard) | Dash app starts without exception; callbacks tested with `dash.testing` where practical; renders with simulated data fixture |
| 10 (Alerts) | Threshold-to-risk-level mapping unit tested for all boundary values; Telegram/Email dispatch mocked (no real messages sent in tests) |
| 11 (Simulator) | Publishes valid payloads matching the MQTT contract (`mqtt_architecture.md §3`) at the configured interval; ingestion consumes them identically to a hand-crafted "fake sensor" publisher; malformed messages are rejected and audit-logged, not silently dropped |
| 12 (Integration) | `tests/e2e/test_full_system.py`: login → patient → MQTT vitals → real-time prediction (real model) → SHAP → automatic alert (Step 10 engine) → acknowledge → dashboard callback rendering → audit trail, all in one continuous run against the live stack |

## 4. Tooling

- `pytest` + `pytest-cov` (target: meaningful coverage on `src/`, not a specific arbitrary %).
- `pytest-asyncio` for FastAPI async routes.
- `httpx` for API TestClient.
- Coverage reports written to `logs/coverage/` (not committed).

## 5. Definition of "Tested" for Each Step

A step is not marked complete until:
1. All new/changed code has at least one passing test.
2. `pytest tests/unit tests/integration -q` exits 0 (integration tests may be skipped with a clear reason if Docker services aren't running, but must pass when they are).
3. Any generated artifact (plot, model file, processed dataset) is verified to exist and be non-empty/non-corrupt.
