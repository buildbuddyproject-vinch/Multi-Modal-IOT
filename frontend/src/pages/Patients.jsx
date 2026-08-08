import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { getLatestPrediction, listPatients, ApiError } from "../api/client";
import RiskBadge from "../components/RiskBadge";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

export default function Patients() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [patients, setPatients] = useState([]);
  const [predictions, setPredictions] = useState({});

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const patientsData = await listPatients(token, { limit: 500 });
        if (cancelled) return;
        setPatients(patientsData);

        const predEntries = await Promise.all(
          patientsData.map(async (p) => [p.patient_id, await getLatestPrediction(token, p.patient_id)])
        );
        if (cancelled) return;
        setPredictions(Object.fromEntries(predEntries));
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

  const sorted = [...patients].sort((a, b) => a.patient_id.localeCompare(b.patient_id));

  return (
    <div>
      <div className="icu-page-header d-flex justify-content-between align-items-start">
        <div>
          <h2><i className="fa-solid fa-user-injured" />Patient Overview</h2>
          <div className="icu-page-subtitle">Patients you&apos;ve admitted and their latest risk assessment</div>
        </div>
        <Link to="/admit-patient" className="btn btn-info btn-sm">
          <i className="fa-solid fa-user-plus me-2" />
          Admit Patient
        </Link>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <AlertBanner color="danger">Could not load patients: {error}</AlertBanner>
      ) : patients.length === 0 ? (
        <AlertBanner color="info">
          <i className="fa-solid fa-circle-info me-2" />
          No patients yet. <Link to="/admit-patient" className="alert-link">Admit your first patient →</Link>
        </AlertBanner>
      ) : (
        <div className="icu-table-card">
          <table className="icu-table table-hover">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>Age</th>
                <th>Sex</th>
                <th>Unit</th>
                <th>Status</th>
                <th>Latest Risk</th>
                <th>Probability</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((p) => {
                const pred = predictions[p.patient_id];
                return (
                  <tr key={p.patient_id}>
                    <td>
                      <Link to={`/patients/${p.patient_id}`}>
                        <i className="fa-solid fa-arrow-up-right-from-square me-2 small" />
                        {p.patient_id}
                      </Link>
                    </td>
                    <td>{p.age ?? "--"}</td>
                    <td>{p.sex ?? "--"}</td>
                    <td>{p.unit_admitted ?? "--"}</td>
                    <td><span className="badge text-bg-secondary">{p.current_status}</span></td>
                    <td>{pred ? <RiskBadge riskLevel={pred.risk_level} /> : <span className="text-muted">--</span>}</td>
                    <td>{pred ? pred.sepsis_probability.toFixed(2) : "--"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
