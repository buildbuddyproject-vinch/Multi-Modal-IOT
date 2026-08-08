"""Premium dark "ICU monitor" visual theme: a deep charcoal/navy surface with
the same saturated cyan/amber/red palette bedside monitors use, so risk levels
read the same way here as they would on real hardware in Phase 2 -- layered
with soft elevation, glassy panels, and refined typography for a polished,
production-grade feel."""
import plotly.graph_objects as go
import plotly.io as pio

BG_DARK = "#070a12"
BG_PANEL = "#10141f"
BG_PANEL_ALT = "#141928"
TEXT_PRIMARY = "#eef1f8"
TEXT_MUTED = "#8993ab"
BORDER = "#212840"

RISK_COLORS = {
    "Low": "#2dd4bf",
    "Medium": "#facc15",
    "High": "#fb923c",
    "Critical": "#fb3a5d",
}

VITALS_LINE_COLOR = "#38bdf8"
ACCENT_GRADIENT = ["#38bdf8", "#818cf8"]
DASHBOARD_TEMPLATE_NAME = "icu_dark"

_icu_dark_template = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_PRIMARY, family="Inter, Segoe UI, sans-serif", size=13),
        colorway=["#38bdf8", "#a78bfa", "#34d399", "#f472b6", "#fbbf24", "#fb923c"],
        xaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER, showspikes=True,
                    spikecolor=TEXT_MUTED, spikethickness=1, spikedash="dot", tickfont=dict(color=TEXT_MUTED)),
        yaxis=dict(gridcolor=BORDER, zerolinecolor=BORDER, linecolor=BORDER, tickfont=dict(color=TEXT_MUTED)),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=TEXT_MUTED)),
        hoverlabel=dict(bgcolor=BG_PANEL_ALT, bordercolor=BORDER, font=dict(color=TEXT_PRIMARY, family="Inter, Segoe UI, sans-serif")),
        hovermode="x unified",
        margin=dict(l=48, r=24, t=32, b=40),
    )
)
pio.templates[DASHBOARD_TEMPLATE_NAME] = _icu_dark_template


def risk_color(risk_level: str) -> str:
    return RISK_COLORS.get(risk_level, TEXT_MUTED)
