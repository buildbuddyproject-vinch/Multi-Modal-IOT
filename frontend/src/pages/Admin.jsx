import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { ApiError, getHealth, listAuditLogs, listUsers, registerUser } from "../api/client";
import { formatTimestamp } from "../utils/formatting";
import Spinner from "../components/Spinner";
import AlertBanner from "../components/AlertBanner";

const ACTION_BADGE_CLASS = {
  login: "text-bg-info",
  prediction_run: "text-bg-secondary",
  alert_dispatched: "text-bg-warning",
  alert_acknowledged: "text-bg-success",
};

export default function Admin() {
  const { isAdmin } = useAuth();

  if (!isAdmin) {
    return <AlertBanner color="danger">This page is restricted to admin accounts.</AlertBanner>;
  }
  return <AdminBody />;
}

function AdminBody() {
  const { token } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);

  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [newRole, setNewRole] = useState("clinician");
  const [creating, setCreating] = useState(false);
  const [createFeedback, setCreateFeedback] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [healthData, usersData, auditData] = await Promise.all([
        getHealth(token),
        listUsers(token),
        listAuditLogs(token, { limit: 100 }),
      ]);
      setHealth(healthData);
      setUsers(usersData);
      setAuditLogs(auditData);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : err.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const handleCreateUser = async (event) => {
    event.preventDefault();
    if (!newUsername || !newPassword) {
      setCreateFeedback({ color: "warning", message: "Username and password are required." });
      return;
    }
    setCreating(true);
    try {
      await registerUser(token, newUsername, newPassword, newRole);
      setCreateFeedback({ color: "success", message: `Created user '${newUsername}' (${newRole}).` });
      setNewUsername("");
      setNewPassword("");
      load();
    } catch (err) {
      setCreateFeedback({ color: "danger", message: `Could not create user: ${err instanceof ApiError ? err.detail : err.message}` });
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="icu-page-header">
        <h2><i className="fa-solid fa-shield-halved" />Admin</h2>
        <div className="icu-page-subtitle">System health, user accounts, and the full audit trail</div>
      </div>

      {loading ? (
        <Spinner />
      ) : error ? (
        <AlertBanner color="danger">Could not load admin data: {error}</AlertBanner>
      ) : (
        <>
          <div className="icu-section-title"><i className="fa-solid fa-heart-pulse" />System Health</div>
          <div className="text-muted mb-4">
            <span className={`badge me-2 ${health.status === "ok" ? "text-bg-success" : "text-bg-danger"}`}>
              {health.status.toUpperCase()}
            </span>
            MongoDB connected: {String(health.mongo_connected)} | API version: {health.version}
          </div>

          <div className="icu-section-title"><i className="fa-solid fa-users" />Users</div>
          <div className="icu-table-card mb-4">
            <table className="icu-table table-hover">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Role</th>
                  <th>Last Login</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.username}>
                    <td>{u.username}</td>
                    <td><span className="badge text-bg-secondary">{u.role}</span></td>
                    <td>{u.last_login || "never"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="icu-section-title"><i className="fa-solid fa-user-plus" />Create User</div>
          <form onSubmit={handleCreateUser} className="row g-2 align-items-center mb-2">
            <div className="col-md-3">
              <input className="form-control" placeholder="Username" value={newUsername} onChange={(e) => setNewUsername(e.target.value)} />
            </div>
            <div className="col-md-3">
              <input className="form-control" type="password" placeholder="Password (min 8 chars)" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            </div>
            <div className="col-md-2">
              <select className="form-select" value={newRole} onChange={(e) => setNewRole(e.target.value)}>
                <option value="clinician">Clinician</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div className="col-md-2">
              <button type="submit" className="btn btn-info" disabled={creating}>
                {creating ? "Creating..." : "Create"}
              </button>
            </div>
          </form>
          {createFeedback ? (
            <div className="small mb-4">
              <AlertBanner color={createFeedback.color}>{createFeedback.message}</AlertBanner>
            </div>
          ) : (
            <div className="mb-4" />
          )}

          <div className="icu-section-title"><i className="fa-solid fa-clipboard-list" />Audit Log</div>
          {auditLogs.length === 0 ? (
            <AlertBanner color="info">
              <i className="fa-solid fa-circle-info me-2" />
              No audit log entries yet.
            </AlertBanner>
          ) : (
            <div className="icu-table-card">
              <table className="icu-table table-hover">
                <thead>
                  <tr>
                    <th>Action</th>
                    <th>Actor</th>
                    <th>Target</th>
                    <th>Time</th>
                  </tr>
                </thead>
                <tbody>
                  {auditLogs.map((log, idx) => (
                    <tr key={idx}>
                      <td><span className={`badge ${ACTION_BADGE_CLASS[log.action] || "text-bg-secondary"}`}>{log.action}</span></td>
                      <td>{log.actor}</td>
                      <td>{`${log.target_type || ""} ${log.target_id || ""}`.trim()}</td>
                      <td>{formatTimestamp(log.timestamp)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  );
}
