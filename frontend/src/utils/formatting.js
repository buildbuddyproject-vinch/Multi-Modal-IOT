// Ported from dashboard/utils/formatting.py. Figure builders return Plotly
// figure objects ({ data, layout }) consumed by react-plotly.js <Plot>.
import { plotlyLayoutBase, riskColor } from "./theme";

export const CORE_VITAL_CHANNELS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "Resp"];

export function formatTimestamp(value) {
  if (!value) return "--";
  const dt = new Date(value);
  if (Number.isNaN(dt.getTime())) return String(value);
  return dt.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}

export function summarizeAlerts(alerts) {
  const counts = { Low: 0, Medium: 0, High: 0, Critical: 0 };
  for (const alert of alerts) {
    if (alert.risk_level in counts) counts[alert.risk_level] += 1;
  }
  return counts;
}

export function summarizePatients(patients) {
  const counts = { active: 0, discharged: 0, deceased: 0 };
  for (const patient of patients) {
    if (patient.current_status in counts) counts[patient.current_status] += 1;
  }
  return counts;
}

function noDataAnnotation() {
  return [{ text: "No data yet", showarrow: false, xref: "paper", yref: "paper", x: 0.5, y: 0.5, font: { size: 16 } }];
}

export function buildVitalsFigure(history, channels = CORE_VITAL_CHANNELS) {
  if (!history || history.length === 0) {
    return { data: [], layout: { ...plotlyLayoutBase, annotations: noDataAnnotation() } };
  }
  const ordered = [...history].sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
  const timestamps = ordered.map((v) => v.timestamp);

  const data = [];
  for (const channel of channels) {
    const values = ordered.map((v) => v.channels?.[channel] ?? null);
    if (values.every((v) => v === null)) continue;
    data.push({
      x: timestamps,
      y: values,
      mode: "lines+markers",
      name: channel,
      connectgaps: true,
      line: { width: 2.5, shape: "spline", smoothing: 0.3 },
      marker: { size: 5 },
    });
  }
  return {
    data,
    layout: {
      ...plotlyLayoutBase,
      legend: { ...plotlyLayoutBase.legend, orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "left", x: 0, title: { text: "Channel" } },
      xaxis: { ...plotlyLayoutBase.xaxis, title: { text: "Time" } },
      yaxis: { ...plotlyLayoutBase.yaxis, title: { text: "Value" } },
    },
  };
}

export function buildPredictionTrendFigure(predictions) {
  if (!predictions || predictions.length === 0) {
    return { data: [], layout: { ...plotlyLayoutBase, annotations: noDataAnnotation() } };
  }
  const ordered = [...predictions].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const timestamps = ordered.map((p) => p.created_at);
  const probabilities = ordered.map((p) => p.sepsis_probability);
  const markerColors = ordered.map((p) => riskColor(p.risk_level));

  return {
    data: [
      {
        x: timestamps,
        y: probabilities,
        mode: "lines+markers",
        name: "Sepsis probability",
        line: { color: "#38bdf8", width: 3, shape: "spline", smoothing: 0.3 },
        marker: { color: markerColors, size: 11, line: { width: 2, color: "#10141f" } },
        fill: "tozeroy",
        fillcolor: "rgba(56, 189, 248, 0.08)",
      },
    ],
    layout: {
      ...plotlyLayoutBase,
      xaxis: { ...plotlyLayoutBase.xaxis, title: { text: "Time" } },
      yaxis: { ...plotlyLayoutBase.yaxis, title: { text: "Sepsis probability" }, range: [0, 1] },
      showlegend: false,
      shapes: [
        {
          type: "line", x0: 0, x1: 1, xref: "paper", y0: 0.5, y1: 0.5, yref: "y",
          line: { color: riskColor("Critical"), dash: "dash" },
        },
      ],
      annotations: [
        { x: 1, y: 0.5, xref: "paper", yref: "y", text: "Critical threshold", showarrow: false,
          font: { color: riskColor("Critical") }, xanchor: "right", yanchor: "bottom" },
      ],
    },
  };
}

export function buildShapFigure(shapValues, topN = 10) {
  if (!shapValues || Object.keys(shapValues).length === 0) {
    return { data: [], layout: { ...plotlyLayoutBase, annotations: noDataAnnotation() } };
  }
  const ranked = Object.entries(shapValues)
    .sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]))
    .slice(0, topN)
    .reverse();
  const features = ranked.map(([k]) => k);
  const contributions = ranked.map(([, v]) => v);
  const colors = contributions.map((v) => (v > 0 ? riskColor("Critical") : riskColor("Low")));

  return {
    data: [
      {
        x: contributions,
        y: features,
        type: "bar",
        orientation: "h",
        marker: { color: colors, line: { width: 0 } },
        text: contributions.map((v) => (v >= 0 ? `+${v.toFixed(3)}` : v.toFixed(3))),
        textposition: "outside",
      },
    ],
    layout: {
      ...plotlyLayoutBase,
      xaxis: { ...plotlyLayoutBase.xaxis, title: { text: "SHAP contribution (+ increases risk)" } },
      yaxis: { ...plotlyLayoutBase.yaxis, title: { text: "Channel" } },
      bargap: 0.35,
      uniformtext: { minsize: 10 },
    },
  };
}
