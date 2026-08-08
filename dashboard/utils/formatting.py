"""Pure data-shaping helpers used by page callbacks. Kept free of any Dash /
Flask imports so they're unit-testable without a running app or browser."""
from datetime import datetime
from typing import Optional

import plotly.graph_objects as go

from dashboard.theme import DASHBOARD_TEMPLATE_NAME, risk_color

CORE_VITAL_CHANNELS = ["HR", "O2Sat", "Temp", "SBP", "MAP", "Resp"]


def format_timestamp(value: Optional[str]) -> str:
    if not value:
        return "--"
    if isinstance(value, datetime):
        dt = value
    else:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def summarize_alerts(alerts: list[dict]) -> dict[str, int]:
    counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for alert in alerts:
        level = alert.get("risk_level")
        if level in counts:
            counts[level] += 1
    return counts


def summarize_patients(patients: list[dict]) -> dict[str, int]:
    counts = {"active": 0, "discharged": 0, "deceased": 0}
    for patient in patients:
        status = patient.get("current_status")
        if status in counts:
            counts[status] += 1
    return counts


def build_vitals_figure(history: list[dict], channels: Optional[list[str]] = None) -> go.Figure:
    channels = channels or CORE_VITAL_CHANNELS
    fig = go.Figure()
    if not history:
        fig.update_layout(template=DASHBOARD_TEMPLATE_NAME, annotations=[_no_data_annotation()])
        return fig

    ordered = sorted(history, key=lambda v: v["timestamp"])
    timestamps = [v["timestamp"] for v in ordered]
    for channel in channels:
        values = [v.get("channels", {}).get(channel) for v in ordered]
        if all(value is None for value in values):
            continue
        fig.add_trace(go.Scatter(
            x=timestamps, y=values, mode="lines+markers", name=channel, connectgaps=True,
            line=dict(width=2.5, shape="spline", smoothing=0.3), marker=dict(size=5),
        ))
    fig.update_layout(
        template=DASHBOARD_TEMPLATE_NAME, legend_title_text="Channel", xaxis_title="Time", yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return fig


def build_prediction_trend_figure(predictions: list[dict]) -> go.Figure:
    fig = go.Figure()
    if not predictions:
        fig.update_layout(template=DASHBOARD_TEMPLATE_NAME, annotations=[_no_data_annotation()])
        return fig

    ordered = sorted(predictions, key=lambda p: p["created_at"])
    timestamps = [p["created_at"] for p in ordered]
    probabilities = [p["sepsis_probability"] for p in ordered]
    marker_colors = [risk_color(p["risk_level"]) for p in ordered]

    fig.add_trace(go.Scatter(
        x=timestamps, y=probabilities, mode="lines+markers", name="Sepsis probability",
        line=dict(color="#38bdf8", width=3, shape="spline", smoothing=0.3),
        marker=dict(color=marker_colors, size=11, line=dict(width=2, color="#10141f")),
        fill="tozeroy", fillcolor="rgba(56, 189, 248, 0.08)",
    ))
    fig.add_hline(y=0.5, line_dash="dash", line_color=risk_color("Critical"), annotation_text="Critical threshold",
                  annotation_font_color=risk_color("Critical"))
    fig.update_layout(
        template=DASHBOARD_TEMPLATE_NAME, xaxis_title="Time", yaxis_title="Sepsis probability",
        yaxis_range=[0, 1], showlegend=False,
    )
    return fig


def build_shap_figure(shap_values: dict[str, float], top_n: int = 10) -> go.Figure:
    fig = go.Figure()
    if not shap_values:
        fig.update_layout(template=DASHBOARD_TEMPLATE_NAME, annotations=[_no_data_annotation()])
        return fig

    ranked = sorted(shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)[:top_n]
    ranked.reverse()  # largest contribution at top of a horizontal bar chart
    features = [k for k, _ in ranked]
    contributions = [v for _, v in ranked]
    colors = [risk_color("Critical") if v > 0 else risk_color("Low") for v in contributions]

    fig.add_trace(go.Bar(
        x=contributions, y=features, orientation="h", marker_color=colors,
        marker_line_width=0, text=[f"{v:+.3f}" for v in contributions], textposition="outside",
    ))
    fig.update_layout(
        template=DASHBOARD_TEMPLATE_NAME, xaxis_title="SHAP contribution (+ increases risk)", yaxis_title="Channel",
        bargap=0.35, uniformtext_minsize=10,
    )
    return fig


def _no_data_annotation() -> dict:
    return dict(text="No data yet", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5, font=dict(size=16))
