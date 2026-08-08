import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Plot from "react-plotly.js";
import { useAuth } from "../context/AuthContext";
import {
  ApiError,
  downloadPatientReport,
  getPatient,
  getPredictionHistory,
  getShapByPrediction,
  getVitalsHistory,
} from "../api/client";
import { buildPredictionTrendFigure, buildShapFigure, buildVitalsFigure, formatTimestamp } from "../utils/formatting";
import KpiCard from "../components/KpiCard";
import RiskBadge from "../components/RiskBadge";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

const TABS = [
  { id: "vitals", label: "Vitals History" },
  { id: "prediction", label: "Prediction Trend" },
  { id: "shap", label: "Explainability (SHAP)" },
];

export default function PatientDetail() {
  const { patientId } = useParams();
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [patient, setPatient] = useState(null);
  const [vitalsHistory, setVitalsHistory] = useState([]);
  const [predictionHistory, setPredictionHistory] = useState([]);
  const [shapExplanation, setShapExplanation] = useState(null);
  const [activeTab, setActiveTab] = useState("vitals");
  const [downloading, setDownloading] = useState(false);
  const [downloadError, setDownloadError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      try {
        const [patientData, vitalsData, predictionsData] = await Promise.all([
          getPatient(token, patientId),
          getVitalsHistory(token, patientId, 1000),
          getPredictionHistory(token, patientId, 200),
        ]);
        const latestPrediction = predictionsData[0] ?? null;
        const shapData = latestPrediction ? await getShapByPrediction(token, latestPrediction.id) : null;
        if (cancelled) return;
        setPatient(patientData);
        setVitalsHistory(vitalsData);
        setPredictionHistory(predictionsData);
        setShapExplanation(shapData);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token, patientId]);

  const handleDownload = async () => {
    setDownloading(true);
    setDownloadError("");
    try {
      const blob = await downloadPatientReport(token, patientId);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${patientId}_sepsis_report.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setDownloadError(err instanceof ApiError ? err.detail : err.message);
    } finally {
      setDownloading(false);
    }
  };

  const latestPrediction = predictionHistory[0] ?? null;

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-3">
        <Link to="/patients">
          <i className="fa-solid fa-arrow-left me-2" />
          Back to patients
        </Link>
        <button type="button" className="btn btn-info btn-sm" onClick={handleDownload} disabled={downloading}>
          <i className="fa-solid fa-file-pdf me-2" />
          {downloading ? "Preparing..." : "Download PDF Report"}
        </button>
      </div>
      {downloadError ? <AlertBanner color="danger" className="mb-3">Could not download report: {downloadError}</AlertBanner> : null}

      {loading ? (
        <Spinner />
      ) : error ? (
        <AlertBanner color="danger">Could not load patient &apos;{patientId}&apos;: {error}</AlertBanner>
      ) : (
        <>
          <Header patient={patient} latestPrediction={latestPrediction} />

          <ul className="nav nav-tabs mt-4">
            {TABS.map((tab) => (
              <li className="nav-item" key={tab.id}>
                <button
                  type="button"
                  className={"nav-link" + (activeTab === tab.id ? " active" : "")}
                  onClick={() => setActiveTab(tab.id)}
                >
                  {tab.label}
                </button>
              </li>
            ))}
          </ul>

          <div className="pt-3">
            {activeTab === "vitals" && <PlotlyFigure figure={buildVitalsFigure(vitalsHistory)} />}
            {activeTab === "prediction" && <PlotlyFigure figure={buildPredictionTrendFigure(predictionHistory)} />}
            {activeTab === "shap" && <ShapTab shapExplanation={shapExplanation} />}
          </div>
        </>
      )}
    </div>
  );
}

function PlotlyFigure({ figure }) {
  return (
    <Plot
      data={figure.data}
      layout={{ ...figure.layout, height: 420 }}
      config={{ displaylogo: false, responsive: true }}
      style={{ width: "100%" }}
      useResizeHandler
    />
  );
}

function Header({ patient, latestPrediction }) {
  const risk = latestPrediction?.risk_level ?? null;
  const prob = latestPrediction ? `${(latestPrediction.sepsis_probability * 100).toFixed(1)}%` : "--";
  const updated = latestPrediction ? formatTimestamp(latestPrediction.created_at) : "--";

  return (
    <div className="row g-3">
      <div className="col-md-6">
        <div className="icu-card h-100" style={{ padding: "1.25rem" }}>
          <h3><i className="fa-solid fa-user me-2 text-info" />{patient.patient_id}</h3>
          <p className="text-muted mb-0">
            Age {patient.age ?? "--"} · Sex {patient.sex ?? "--"} · Unit {patient.unit_admitted ?? "--"} · Status {patient.current_status}
          </p>
        </div>
      </div>
      <div className="col-md-3">
        <KpiCard title="Sepsis Probability" value={prob} subtitle={`Updated ${updated}`} color="#38bdf8" icon="fa-solid fa-heart-pulse" />
      </div>
      <div className="col-md-3">
        <div className="icu-card h-100" style={{ padding: "1.25rem" }}>
          <div className="icu-kpi-title mb-2">Risk Level</div>
          <RiskBadge riskLevel={risk} />
        </div>
      </div>
    </div>
  );
}

function ShapTab({ shapExplanation }) {
  if (!shapExplanation) {
    return (
      <AlertBanner color="info">
        <i className="fa-solid fa-circle-info me-2" />
        No SHAP explanation available yet for this patient&apos;s latest prediction.
      </AlertBanner>
    );
  }
  const features = shapExplanation.top_contributing_features || [];
  return (
    <div>
      <PlotlyFigure figure={buildShapFigure(shapExplanation.shap_values)} />
      <div className="icu-section-title mt-2">
        <i className="fa-solid fa-list-ol" />Top Contributing Channels
      </div>
      <div className="icu-table-card">
        <table className="icu-table table-hover">
          <thead>
            <tr>
              <th>Channel</th>
              <th>Observed Value</th>
              <th>Contribution</th>
            </tr>
          </thead>
          <tbody>
            {features.map((f) => (
              <tr key={f.feature}>
                <td>{f.feature}</td>
                <td>{f.value.toFixed(2)}</td>
                <td>{f.contribution >= 0 ? `+${f.contribution.toFixed(4)}` : f.contribution.toFixed(4)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
