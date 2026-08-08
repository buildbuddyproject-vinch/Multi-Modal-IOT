import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

const FEATURES = [
  { icon: "fa-solid fa-brain", label: "AI-powered sepsis risk prediction, updated in real time" },
  { icon: "fa-solid fa-magnifying-glass-chart", label: "Explainable AI -- see exactly why a risk score changed" },
  { icon: "fa-solid fa-shield-halved", label: "Private, per-clinician patient data with a full audit trail" },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
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
      <div className="icu-login-shell">
        <div className="icu-login-brand-panel">
          <div className="icu-login-brand-mark">
            <div className="icu-sidebar-brand-icon">🩺</div>
            <div>
              <div className="icu-login-brand-name">Sepsis ICU Monitor</div>
              <div className="icu-login-brand-tag">Multi-Modal Prediction</div>
            </div>
          </div>

          <div className="icu-login-brand-heading">
            <h1>Catch sepsis hours before it becomes critical.</h1>
            <p>
              A hybrid deep-learning system that watches ICU vitals continuously and flags deteriorating patients
              before a busy unit would.
            </p>

            <div className="icu-login-features">
              {FEATURES.map((f) => (
                <div className="icu-login-feature" key={f.label}>
                  <i className={f.icon} />
                  <span>{f.label}</span>
                </div>
              ))}
            </div>
          </div>

          <div className="icu-login-brand-footnote">
            Research/educational system -- not a certified medical device.
          </div>
        </div>

        <div className="icu-login-form-panel">
          <div className="icu-login-card">
            <div className="icu-login-icon">🩺</div>
            <div className="icu-login-title">Welcome back</div>
            <div className="icu-login-subtitle">Log in to your Sepsis ICU Monitor account</div>

            <form onSubmit={handleSubmit}>
              <label className="form-label" htmlFor="login-username">Username</label>
              <div className="icu-login-input-group mb-3">
                <i className="fa-solid fa-user icu-input-icon" />
                <input
                  id="login-username"
                  className="form-control"
                  type="text"
                  placeholder="e.g. dr_smith"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </div>

              <label className="form-label" htmlFor="login-password">Password</label>
              <div className="icu-login-input-group mb-3">
                <i className="fa-solid fa-lock icu-input-icon" />
                <input
                  id="login-password"
                  className="form-control"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="icu-toggle-visibility"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  tabIndex={-1}
                >
                  <i className={showPassword ? "fa-solid fa-eye-slash" : "fa-solid fa-eye"} />
                </button>
              </div>

              <button type="submit" className="btn btn-info w-100 mt-2" disabled={submitting}>
                <i className="fa-solid fa-arrow-right-to-bracket me-2" />
                {submitting ? "Logging in..." : "Log in"}
              </button>

              <div className="text-danger small text-center mt-2">{error}</div>
            </form>

            <div className="icu-login-footnote">
              New accounts are provisioned by an admin -- no self-registration.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
