"""Pop-up toast for a single High/Critical risk alert (dashboard/app.py's
global poller renders one of these per newly-seen alert, stacked top-right,
on every page -- not just the Alerts page)."""
import dash_bootstrap_components as dbc
from dash import dcc, html

from dashboard.utils.formatting import format_timestamp

_RISK_META = {
    "Critical": {"icon": "danger", "symbol": "fa-solid fa-triangle-exclamation", "label": "Critical Risk Alert"},
    "High": {"icon": "warning", "symbol": "fa-solid fa-circle-exclamation", "label": "High Risk Alert"},
}


def build_alert_toast(alert: dict) -> dbc.Toast:
    meta = _RISK_META.get(alert["risk_level"], _RISK_META["High"])

    header = html.Span(
        [html.I(className=f"{meta['symbol']} me-2"), meta["label"]],
        className="d-flex align-items-center",
    )

    body = html.Div(
        [
            dcc.Link(alert["patient_id"], href=f"/patients/{alert['patient_id']}", className="fw-bold d-block mb-1"),
            html.Div(alert["message"], className="small mb-1"),
            html.Div(format_timestamp(alert.get("created_at")), className="text-muted small"),
        ]
    )

    return dbc.Toast(
        body,
        header=header,
        icon=meta["icon"],
        duration=18000,
        dismissable=True,
        is_open=True,
        class_name=f"icu-alert-toast icu-alert-toast-{alert['risk_level'].lower()}",
    )
