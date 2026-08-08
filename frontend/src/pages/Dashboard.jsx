import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listAlerts, listPatients, ApiError } from "../api/client";
import { summarizeAlerts, summarizePatients, formatTimestamp } from "../utils/formatting";
import KpiCard from "../components/KpiCard";
import RiskBadge from "../components/RiskBadge";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

export default function Dashboard() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [patients, setPatients] = useState([]);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [patientsData, alertsData] = await Promise.all([
          listPatients(token, { limit: 500 }),
          listAlerts(token, { acknowledged: false, limit: 200 }),
        ]);
        if (cancelled) return;
        setPatients(patientsData);
        setAlerts(alertsData);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.detail : err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const patientCounts = summarizePatients(patients);
  const alertCounts = summarizeAlerts(alerts);

  return (
    <div>
      <div className="icu-page-header">
        <h2><i className="fa-solid fa-gauge-high" />ICU Overview</h2>
        <div className="icu-page-subtitle">Real-time patient risk summary across the unit</div>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <AlertBanner color="danger">Could not load overview: {error}</AlertBanner>
      ) : (
        <div className="row g-3 mb-1">
          <div className="col-md-3">
            <KpiCard title="Active Patients" value={patientCounts.active} subtitle={`${patients.length} total`} color="#38bdf8" icon="fa-solid fa-user-injured" />
          </div>
          <div className="col-md-3">
            <KpiCard title="Unacknowledged Alerts" value={alerts.length} color="#facc15" icon="fa-solid fa-bell" />
          </div>
          <div className="col-md-3">
            <KpiCard title="Critical Alerts" value={alertCounts.Critical} color="#fb3a5d" icon="fa-solid fa-triangle-exclamation" />
          </div>
          <div className="col-md-3">
            <KpiCard title="High Alerts" value={alertCounts.High} color="#fb923c" icon="fa-solid fa-arrow-trend-up" />
          </div>
        </div>
      )}

      <div className="icu-section-title mt-4">
        <i className="fa-solid fa-bell" />Recent Alerts
      </div>

      {loading ? (
        <Spinner />
      ) : error ? null : alerts.length === 0 ? (
        <AlertBanner color="success">
          <i className="fa-solid fa-circle-check me-2" />
          No unacknowledged alerts. All clear.
        </AlertBanner>
      ) : (
        <div className="icu-table-card">
          <table className="icu-table table-hover">
            <thead>
              <tr>
                <th>Risk</th>
                <th>Patient</th>
                <th>Message</th>
                <th>Time</th>
              </tr>
            </thead>
            <tbody>
              {alerts.slice(0, 15).map((a) => (
                <tr key={a.id}>
                  <td><RiskBadge riskLevel={a.risk_level} /></td>
                  <td><Link to={`/patients/${a.patient_id}`}>{a.patient_id}</Link></td>
                  <td>{a.message}</td>
                  <td>{formatTimestamp(a.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
