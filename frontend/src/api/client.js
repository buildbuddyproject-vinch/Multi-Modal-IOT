// Thin HTTP client the React app uses to talk to the FastAPI backend --
// a direct port of the old dashboard/api_client.py's method surface. The
// backend already has CORS wide open (src/api/main.py), so this calls it
// directly from the browser -- no Node/Flask proxy in between.
import axios from "axios";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export class ApiError extends Error {
  constructor(statusCode, detail) {
    super(`[${statusCode}] ${detail}`);
    this.statusCode = statusCode;
    this.detail = detail;
  }
}

function buildClient(token) {
  const instance = axios.create({
    baseURL: API_BASE_URL,
    timeout: 15000,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  instance.interceptors.response.use(
    (resp) => resp,
    (error) => {
      if (error.response) {
        const detail = error.response.data?.detail ?? error.response.statusText;
        throw new ApiError(error.response.status, typeof detail === "string" ? detail : JSON.stringify(detail));
      }
      throw new ApiError(503, `could not reach API backend: ${error.message}`);
    }
  );
  return instance;
}

// Every function below takes `token` first so callers (AuthContext / pages)
// don't need to construct a client object -- matches how each old Dash
// callback opened a fresh ApiClient(token=...) per request.

// --- auth ---
export async function login(username, password) {
  const resp = await buildClient(null).post("/auth/login", { username, password });
  return resp.data; // { access_token, username, role }
}

export async function getMe(token) {
  return (await buildClient(token).get("/auth/me")).data;
}

export async function listUsers(token) {
  return (await buildClient(token).get("/auth/users")).data;
}

export async function registerUser(token, username, password, role) {
  return (await buildClient(token).post("/auth/register", { username, password, role })).data;
}

// --- health ---
export async function getHealth(token) {
  return (await buildClient(token).get("/health")).data;
}

// --- audit log ---
export async function listAuditLogs(token, { action, limit = 100 } = {}) {
  const params = { limit, ...(action ? { action } : {}) };
  return (await buildClient(token).get("/audit-logs", { params })).data;
}

// --- patients ---
export async function listPatients(token, { status, limit = 100 } = {}) {
  const params = { limit, ...(status ? { status_filter: status } : {}) };
  return (await buildClient(token).get("/patients", { params })).data;
}

export async function getPatient(token, patientId) {
  return (await buildClient(token).get(`/patients/${patientId}`)).data;
}

export async function createPatient(token, { patientId, sourceDataset, age, sex, unitAdmitted, currentStatus = "active" }) {
  const payload = { patient_id: patientId, source_dataset: sourceDataset, current_status: currentStatus };
  if (age !== null && age !== undefined && age !== "") payload.age = Number(age);
  if (sex) payload.sex = sex;
  if (unitAdmitted) payload.unit_admitted = unitAdmitted;
  return (await buildClient(token).post("/patients", payload)).data;
}

// --- vitals ---
export async function getLatestVitals(token, patientId) {
  try {
    return (await buildClient(token).get(`/vitals/${patientId}/latest`)).data;
  } catch (err) {
    if (err instanceof ApiError && err.statusCode === 404) return null;
    throw err;
  }
}

export async function getVitalsHistory(token, patientId, limit = 1000) {
  return (await buildClient(token).get(`/vitals/${patientId}/history`, { params: { limit } })).data;
}

// --- predictions ---
export async function getLatestPrediction(token, patientId) {
  try {
    return (await buildClient(token).get(`/predictions/${patientId}/latest`)).data;
  } catch (err) {
    if (err instanceof ApiError && err.statusCode === 404) return null;
    throw err;
  }
}

export async function getPredictionHistory(token, patientId, limit = 100) {
  return (await buildClient(token).get(`/predictions/${patientId}/history`, { params: { limit } })).data;
}

// --- shap ---
export async function getShapByPrediction(token, predictionId) {
  try {
    return (await buildClient(token).get(`/shap/prediction/${predictionId}`)).data;
  } catch (err) {
    if (err instanceof ApiError && err.statusCode === 404) return null;
    throw err;
  }
}

// --- alerts ---
export async function listAlerts(token, { patientId, acknowledged, riskLevel, limit = 100 } = {}) {
  const params = { limit };
  if (patientId !== undefined && patientId !== null) params.patient_id = patientId;
  if (acknowledged !== undefined && acknowledged !== null) params.acknowledged = acknowledged;
  if (riskLevel) params.risk_level = riskLevel;
  return (await buildClient(token).get("/alerts", { params })).data;
}

export async function acknowledgeAlert(token, alertId, acknowledgedBy) {
  return (await buildClient(token).patch(`/alerts/${alertId}/acknowledge`, { acknowledged_by: acknowledgedBy })).data;
}

// --- reports ---
export async function downloadPatientReport(token, patientId) {
  const resp = await buildClient(token).get(`/patients/${patientId}/report`, { responseType: "blob" });
  return resp.data; // Blob
}
