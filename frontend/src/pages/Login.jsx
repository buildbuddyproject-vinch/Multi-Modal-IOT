import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const redirectTo = location.state?.from?.pathname || "/";

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!username || !password) {
      setError("Enter both a username and password.");
      return;
    }
    setSubmitting(true);
    setError("");
    try {
      await login(username, password);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.statusCode === 401) {
        setError("Invalid username or password.");
      } else {
        setError(`Login failed: ${err.message}`);
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="icu-login-page">
      <div className="icu-login-card">
        <div className="icu-login-icon">🩺</div>
        <div className="icu-login-title">Sepsis ICU Monitor</div>
        <div className="icu-login-subtitle">Multi-Modal IoT &amp; Deep Learning Sepsis Prediction</div>

        <form onSubmit={handleSubmit}>
          <label className="form-label" htmlFor="login-username">Username</label>
          <input
            id="login-username"
            className="form-control mb-3"
            type="text"
            placeholder="e.g. dr_smith"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
          />

          <label className="form-label" htmlFor="login-password">Password</label>
          <input
            id="login-password"
            className="form-control mb-3"
            type="password"
            placeholder="••••••••"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          <button type="submit" className="btn btn-info w-100 mb-2" disabled={submitting}>
            <i className="fa-solid fa-arrow-right-to-bracket me-2" />
            {submitting ? "Logging in..." : "Log in"}
          </button>

          <div className="text-danger small text-center">{error}</div>
        </form>
      </div>
    </div>
  );
}
