// Ported from dashboard/theme.py -- same palette, same risk-color mapping,
// same Plotly layout template so the charts read identically to the Dash version.
export const RISK_COLORS = {
  Low: "#2dd4bf",
  Medium: "#facc15",
  High: "#fb923c",
  Critical: "#fb3a5d",
};

export const TEXT_PRIMARY = "#eef1f8";
export const TEXT_MUTED = "#8993ab";
export const BORDER = "#212840";
export const BG_PANEL_ALT = "#141928";

export function riskColor(riskLevel) {
  return RISK_COLORS[riskLevel] || TEXT_MUTED;
}

export const plotlyLayoutBase = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: { color: TEXT_PRIMARY, family: "Inter, Segoe UI, sans-serif", size: 13 },
  colorway: ["#38bdf8", "#a78bfa", "#34d399", "#f472b6", "#fbbf24", "#fb923c"],
  xaxis: {
    gridcolor: BORDER,
    zerolinecolor: BORDER,
    linecolor: BORDER,
    showspikes: true,
    spikecolor: TEXT_MUTED,
    spikethickness: 1,
    spikedash: "dot",
    tickfont: { color: TEXT_MUTED },
  },
  yaxis: { gridcolor: BORDER, zerolinecolor: BORDER, linecolor: BORDER, tickfont: { color: TEXT_MUTED } },
  legend: { bgcolor: "rgba(0,0,0,0)", font: { color: TEXT_MUTED } },
  hoverlabel: { bgcolor: BG_PANEL_ALT, bordercolor: BORDER, font: { color: TEXT_PRIMARY, family: "Inter, Segoe UI, sans-serif" } },
  hovermode: "x unified",
  margin: { l: 48, r: 24, t: 32, b: 40 },
  autosize: true,
};
