// Global red/orange popup toasts for new High/Critical alerts -- ported from
// dashboard/app.py's poll_critical_alerts callback + dashboard/components/alert_toast.py.
// Polls every 8s (same interval the Dash version used) from wherever the user
// currently is, not just the Alerts page. Only ever *appends* newly-seen
// alerts so toasts already on screen aren't reset by the next poll.
import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { listAlerts } from "../api/client";
import { formatTimestamp } from "../utils/formatting";

const POLL_INTERVAL_MS = 8000;
const URGENT_RISK_LEVELS = new Set(["High", "Critical"]);
const MAX_TOASTS = 6;
const MAX_SEEN_IDS = 300;
const AUTO_DISMISS_MS = 18000;

const RISK_META = {
  Critical: { symbol: "fa-solid fa-triangle-exclamation", label: "Critical Risk Alert" },
  High: { symbol: "fa-solid fa-circle-exclamation", label: "High Risk Alert" },
};

export default function AlertToastStack() {
  const { token, isAuthenticated } = useAuth();
  const [toasts, setToasts] = useState([]);
  const seenIdsRef = useRef(new Set());

  const poll = useCallback(async () => {
    if (!isAuthenticated || !token) return;
    let alerts;
    try {
      alerts = await listAlerts(token, { acknowledged: false, limit: 50 });
    } catch {
      return; // same as the old callback: silently skip this tick on API error
    }
    const newAlerts = alerts.filter((a) => URGENT_RISK_LEVELS.has(a.risk_level) && !seenIdsRef.current.has(a.id));
    if (newAlerts.length === 0) return;

    for (const a of newAlerts) seenIdsRef.current.add(a.id);
    if (seenIdsRef.current.size > MAX_SEEN_IDS) {
      seenIdsRef.current = new Set([...seenIdsRef.current].slice(-MAX_SEEN_IDS));
    }
    setToasts((prev) => [...prev, ...newAlerts].slice(-MAX_TOASTS));
  }, [isAuthenticated, token]);

  useEffect(() => {
    if (!isAuthenticated) return undefined;
    const id = setInterval(poll, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, [isAuthenticated, poll]);

  const dismiss = (alertId) => setToasts((prev) => prev.filter((t) => t.id !== alertId));

  useEffect(() => {
    const timers = toasts.map((t) => setTimeout(() => dismiss(t.id), AUTO_DISMISS_MS));
    return () => timers.forEach(clearTimeout);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [toasts]);

  if (toasts.length === 0) return null;

  return (
    <div className="icu-toast-stack">
      {toasts.map((alert) => {
        const meta = RISK_META[alert.risk_level] || RISK_META.High;
        return (
          <div key={alert.id} className={`icu-alert-toast icu-alert-toast-${alert.risk_level.toLowerCase()}`}>
            <div className="toast-header">
              <span className="d-flex align-items-center">
                <i className={`${meta.symbol} me-2`} />
                {meta.label}
              </span>
              <button type="button" className="btn-close" aria-label="Close" onClick={() => dismiss(alert.id)}>
                ✕
              </button>
            </div>
            <div className="toast-body">
              <Link to={`/patients/${alert.patient_id}`} className="fw-bold d-block mb-1">
                {alert.patient_id}
              </Link>
              <div className="small mb-1">{alert.message}</div>
              <div className="text-muted small">{formatTimestamp(alert.created_at)}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
