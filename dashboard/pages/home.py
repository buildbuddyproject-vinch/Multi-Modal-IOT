import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.components.cards import kpi_card, risk_badge
from dashboard.utils.formatting import format_timestamp, summarize_alerts, summarize_patients

dash.register_page(__name__, path="/", name="Dashboard")


def layout():
    return html.Div(
        [
            dcc.Interval(id="home-init", interval=200, max_intervals=1),
            html.Div(
                [
                    html.H2([html.I(className="fa-solid fa-gauge-high"), "ICU Overview"]),
                    html.Div("Real-time patient risk summary across the unit", className="icu-page-subtitle"),
                ],
                className="icu-page-header",
            ),
            dbc.Spinner(html.Div(id="home-kpi-row"), color="info", size="sm"),
            html.Div(
                [html.I(className="fa-solid fa-bell"), "Recent Alerts"],
                className="icu-section-title mt-4",
            ),
            dbc.Spinner(html.Div(id="home-recent-alerts"), color="info", size="sm"),
        ]
    )


@callback(
    Output("home-kpi-row", "children"),
    Output("home-recent-alerts", "children"),
    Input("home-init", "n_intervals"),
)
def load_overview(_n_intervals):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            patients = client.list_patients(limit=500)
            alerts = client.list_alerts(acknowledged=False, limit=200)
    except ApiError as exc:
        error = dbc.Alert(f"Could not load overview: {exc.detail}", color="danger")
        return error, ""

    patient_counts = summarize_patients(patients)
    alert_counts = summarize_alerts(alerts)

    kpi_row = dbc.Row(
        [
            dbc.Col(kpi_card("Active Patients", patient_counts["active"], f"{len(patients)} total", "#38bdf8", "fa-solid fa-user-injured"), md=3, class_name="mb-3"),
            dbc.Col(kpi_card("Unacknowledged Alerts", len(alerts), "", "#facc15", "fa-solid fa-bell"), md=3, class_name="mb-3"),
            dbc.Col(kpi_card("Critical Alerts", alert_counts["Critical"], "", "#fb3a5d", "fa-solid fa-triangle-exclamation"), md=3, class_name="mb-3"),
            dbc.Col(kpi_card("High Alerts", alert_counts["High"], "", "#fb923c", "fa-solid fa-arrow-trend-up"), md=3, class_name="mb-3"),
        ]
    )

    if not alerts:
        alerts_view = dbc.Alert([html.I(className="fa-solid fa-circle-check me-2"), "No unacknowledged alerts. All clear."], color="success")
    else:
        rows = [
            html.Tr([
                html.Td(risk_badge(a["risk_level"])),
                html.Td(dcc.Link(a["patient_id"], href=f"/patients/{a['patient_id']}")),
                html.Td(a["message"]),
                html.Td(format_timestamp(a.get("created_at"))),
            ])
            for a in alerts[:15]
        ]
        alerts_view = dbc.Table(
            [html.Thead(html.Tr([html.Th("Risk"), html.Th("Patient"), html.Th("Message"), html.Th("Time")])), html.Tbody(rows)],
            bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
        )

    return kpi_row, alerts_view
