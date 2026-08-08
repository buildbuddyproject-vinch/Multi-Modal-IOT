import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const NAV_ITEMS = [
  { label: "Dashboard", to: "/", icon: "fa-solid fa-gauge-high", end: true },
  { label: "Patients", to: "/patients", icon: "fa-solid fa-user-injured" },
  { label: "Admit Patient", to: "/admit-patient", icon: "fa-solid fa-user-plus" },
  { label: "Live Monitoring", to: "/live-monitoring", icon: "fa-solid fa-wave-square" },
  { label: "Alerts", to: "/alerts", icon: "fa-solid fa-bell" },
];

export default function Sidebar() {
  const { username, role, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  const navItems = isAdmin ? [...NAV_ITEMS, { label: "Admin", to: "/admin", icon: "fa-solid fa-shield-halved" }] : NAV_ITEMS;

  const initials =
    (username || "?")
      .replace(/[._]/g, " ")
      .split(" ")
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0])
      .join("")
      .toUpperCase() || (username || "??").slice(0, 2).toUpperCase();

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="icu-sidebar">
      <div className="icu-sidebar-brand">
        <div className="icu-sidebar-brand-icon">🩺</div>
        <div className="icu-sidebar-brand-text">
          <div className="icu-sidebar-brand-title">Sepsis ICU Monitor</div>
          <div className="icu-sidebar-brand-subtitle">Multi-Modal Prediction</div>
        </div>
      </div>

      <div className="icu-nav">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => "icu-nav-link" + (isActive ? " active" : "")}
          >
            <i className={item.icon} />
            <span>{item.label}</span>
          </NavLink>
        ))}
      </div>

      <div className="icu-sidebar-footer">
        <div className="icu-user-chip">
          <div className="icu-user-avatar">{initials}</div>
          <div className="icu-user-meta">
            <div className="icu-user-name">{username}</div>
            <div className="icu-user-role">{role}</div>
          </div>
        </div>
        <button type="button" className="btn btn-outline-secondary btn-sm w-100" onClick={handleLogout}>
          <i className="fa-solid fa-arrow-right-from-bracket me-2" />
          Log out
        </button>
      </div>
    </div>
  );
}
