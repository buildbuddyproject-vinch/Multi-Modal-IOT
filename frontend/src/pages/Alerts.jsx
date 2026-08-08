import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError, acknowledgeAlert, listAlerts } from "../api/client";
import { formatTimestamp } from "../utils/formatting";
import RiskBadge from "../components/RiskBadge";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

const RISK_LEVELS = ["Low", "Medium", "High", "Critical"];

export default function Alerts() {
  const { token, username } = useAuth();
  const [riskFilter, setRiskFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [ackingId, setAckingId] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const acknowledged = { true: true, false: false }[statusFilter];
    try {
      const data = await listAlerts(token, {
        riskLevel: riskFilter || undefined,
        acknowledged,
        limit: 200,
      });
      setAlerts(data);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : err.message);
    } finally {
      setLoading(false);
    }
  }, [token, riskFilter, statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleAcknowledge = async (alertId) => {
    setAckingId(alertId);
    try {
      await acknowledgeAlert(token, alertId, username);
    } catch {
      // surfaced again via the refreshed table not showing it as acknowledged
    } finally {
      setAckingId(null);
      load();
    }
  };

  return (
    <div>
      <div className="icu-page-header">
        <h2><i className="fa-solid fa-bell" />Alerts</h2>
        <div className="icu-page-subtitle">Clinical alerts triggered by the sepsis prediction engine</div>
      </div>

      <div className="row mb-4">
        <div className="col-md-3">
          <select className="form-select" value={riskFilter} onChange={(e) => setRiskFilter(e.target.value)}>
            <option value="">Filter by risk level</option>
            {RISK_LEVELS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </div>
        <div className="col-md-3">
          <select className="form-select" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">Filter by status</option>
            <option value="false">Unacknowledged</option>
            <option value="true">Acknowledged</option>
          </select>
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <AlertBanner color="danger">Could not load alerts: {error}</AlertBanner>
      ) : alerts.length === 0 ? (
        <AlertBanner color="info">
          <i className="fa-solid fa-circle-info me-2" />
          No alerts match this filter.
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
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td><RiskBadge riskLevel={a.risk_level} /></td>
                  <td><Link to={`/patients/${a.patient_id}`}>{a.patient_id}</Link></td>
                  <td>{a.message}</td>
                  <td>{formatTimestamp(a.created_at)}</td>
                  <td>
                    {a.acknowledged ? (
                      <span className="text-muted small">
                        <i className="fa-solid fa-check me-1" />
                        Ack&apos;d by {a.acknowledged_by}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-warning btn-sm"
                        disabled={ackingId === a.id}
                        onClick={() => handleAcknowledge(a.id)}
                      >
                        {ackingId === a.id ? "Acknowledging..." : "Acknowledge"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
