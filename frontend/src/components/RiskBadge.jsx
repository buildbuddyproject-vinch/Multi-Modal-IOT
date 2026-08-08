import { riskColor } from "../utils/theme";

export default function RiskBadge({ riskLevel }) {
  const color = riskColor(riskLevel);
  return (
    <span className="icu-risk-badge" style={{ backgroundColor: `${color}1f`, color }}>
      <span className="icu-risk-dot" style={{ backgroundColor: color, color }} />
      {riskLevel || "Unknown"}
    </span>
  );
}
