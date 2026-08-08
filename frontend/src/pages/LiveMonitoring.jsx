import { useEffect, useState } from "react";
import Plot from "react-plotly.js";
import { useAuth } from "../context/AuthContext";
import { ApiError, getLatestPrediction, getLatestVitals, getVitalsHistory, listPatients } from "../api/client";
import { buildVitalsFigure, formatTimestamp } from "../utils/formatting";
import KpiCard from "../components/KpiCard";
import RiskBadge from "../components/RiskBadge";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

const POLL_SECONDS = Number(import.meta.env.VITE_LIVE_MONITORING_POLL_SECONDS || 5);

export default function LiveMonitoring() {
  const { token } = useAuth();
  const [options, setOptions] = useState([]);
  const [patientId, setPatientId] = useState(null);
  const [optionsLoading, setOptionsLoading] = useState(true);
  const [body, setBody] = useState({ loading: true, error: null, vitals: null, vitalsHistory: [], prediction: null });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const patients = await listPatients(token, { status: "active", limit: 500 });
        if (cancelled) return;
        const sorted = [...patients].sort((a, b) => a.patient_id.localeCompare(b.patient_id));
        setOptions(sorted.map((p) => p.patient_id));
        setPatientId(sorted[0]?.patient_id ?? null);
      } catch {
        if (!cancelled) setOptions([]);
      } finally {
        if (!cancelled) setOptionsLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  useEffect(() => {
    if (!patientId) {
      setBody({ loading: false, error: null, vitals: null, vitalsHistory: [], prediction: null });
      return undefined;
    }
    let cancelled = false;

    const refresh = async () => {
      try {
        const [vitals, vitalsHistory, prediction] = await Promise.all([
          getLatestVitals(token, patientId),
          getVitalsHistory(token, patientId, 50),
          getLatestPrediction(token, patientId),
        ]);
        if (cancelled) return;
        setBody({ loading: false, error: null, vitals, vitalsHistory, prediction });
      } catch (err) {
        if (!cancelled) setBody((prev) => ({ ...prev, loading: false, error: err instanceof ApiError ? err.detail : err.message }));
      }
    };

    setBody((prev) => ({ ...prev, loading: true }));
    refresh();
    const id = setInterval(refresh, POLL_SECONDS * 1000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [token, patientId]);

  return (
    <div>
      <div className="icu-page-header">
        <h2>
          <i className="fa-solid fa-wave-square" />Live Monitoring
          <span className="icu-live-dot ms-2" />
        </h2>
        <div className="icu-page-subtitle">
          Polls the latest vitals/prediction for the selected patient every {POLL_SECONDS.toFixed(0)}s. In Phase 2
          this same view reflects real ESP32 sensor readings the moment they land in MongoDB via MQTT.
        </div>
      </div>

      <div className="row mb-4">
        <div className="col-md-4">
          <select
            className="form-select"
            value={patientId ?? ""}
            disabled={optionsLoading || options.length === 0}
            onChange={(e) => setPatientId(e.target.value || null)}
          >
            {options.length === 0 ? (
              <option value="">{optionsLoading ? "Loading..." : "No active patients"}</option>
            ) : (
              options.map((id) => (
                <option key={id} value={id}>{id}</option>
              ))
            )}
          </select>
        </div>
      </div>

      {body.loading ? (
        <Spinner />
      ) : !patientId ? (
        <AlertBanner color="info">No active patients to monitor.</AlertBanner>
      ) : body.error ? (
        <AlertBanner color="danger">Could not load live data: {body.error}</AlertBanner>
      ) : (
        <div>
          <div className="row g-3 mb-3">
            <div className="col-md-4">
              <KpiCard title="Last Reading" value={body.vitals ? formatTimestamp(body.vitals.timestamp) : "--"} subtitle={body.vitals?.source ?? ""} color="#a78bfa" icon="fa-solid fa-clock" />
            </div>
            <div className="col-md-4">
              <KpiCard title="Sepsis Probability" value={body.prediction ? `${(body.prediction.sepsis_probability * 100).toFixed(1)}%` : "--"} color="#38bdf8" icon="fa-solid fa-heart-pulse" />
            </div>
            <div className="col-md-4">
              <div className="icu-card h-100" style={{ padding: "1.25rem" }}>
                <div className="icu-kpi-title mb-2">Risk Level</div>
                <RiskBadge riskLevel={body.prediction?.risk_level ?? null} />
              </div>
            </div>
          </div>
          <Plot
            data={buildVitalsFigure(body.vitalsHistory).data}
            layout={{ ...buildVitalsFigure(body.vitalsHistory).layout, height: 420 }}
            config={{ displaylogo: false, responsive: true }}
            style={{ width: "100%" }}
            useResizeHandler
          />
        </div>
      )}
    </div>
  );
}
