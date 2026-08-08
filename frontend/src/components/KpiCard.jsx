export default function KpiCard({ title, value, subtitle = "", color = "#38bdf8", icon = "fa-solid fa-chart-line" }) {
  return (
    <div className="icu-card icu-kpi-card h-100" style={{ padding: "1.1rem 1.25rem" }}>
      <div className="icu-kpi-accent" style={{ backgroundColor: color }} />
      <div className="icu-kpi-icon" style={{ backgroundColor: `${color}22`, color }}>
        <i className={icon} />
      </div>
      <div className="icu-kpi-title">{title}</div>
      <div className="icu-kpi-value" style={{ color }}>{String(value)}</div>
      {subtitle ? <div className="text-muted small mt-1">{subtitle}</div> : null}
    </div>
  );
}
