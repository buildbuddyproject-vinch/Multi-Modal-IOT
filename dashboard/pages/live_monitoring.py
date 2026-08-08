import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.components.cards import kpi_card, risk_badge
from dashboard.config import get_dashboard_settings
from dashboard.utils.formatting import build_vitals_figure, format_timestamp

dash.register_page(__name__, path="/live-monitoring", name="Live Monitoring")


def layout():
    settings = get_dashboard_settings()
    return html.Div(
        [
            dcc.Interval(id="live-monitoring-init", interval=200, max_intervals=1),
            dcc.Interval(id="live-monitoring-poll", interval=int(settings.live_monitoring_poll_seconds * 1000)),
            html.Div(
                [
                    html.H2([html.I(className="fa-solid fa-wave-square"), "Live Monitoring", html.Span(className="icu-live-dot ms-2")]),
                    html.Div(
                        "Polls the latest vitals/prediction for the selected patient every "
                        f"{settings.live_monitoring_poll_seconds:.0f}s. In Phase 2 this same view "
                        "reflects real ESP32 sensor readings the moment they land in MongoDB via MQTT.",
                        className="icu-page-subtitle",
                    ),
                ],
                className="icu-page-header",
            ),
            dbc.Row(
                dbc.Col(
                    dcc.Dropdown(id="live-monitoring-patient-select", placeholder="Select a patient...", clearable=False),
                    md=4,
                ),
                class_name="mb-4",
            ),
            dbc.Spinner(html.Div(id="live-monitoring-body"), color="info", size="sm"),
        ]
    )


@callback(
    Output("live-monitoring-patient-select", "options"),
    Output("live-monitoring-patient-select", "value"),
    Input("live-monitoring-init", "n_intervals"),
)
def load_patient_options(_n_intervals):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            patients = client.list_patients(status="active", limit=500)
    except ApiError:
        return [], None

    options = [{"label": p["patient_id"], "value": p["patient_id"]} for p in sorted(patients, key=lambda p: p["patient_id"])]
    return options, (options[0]["value"] if options else None)


@callback(
    Output("live-monitoring-body", "children"),
    Input("live-monitoring-poll", "n_intervals"),
    Input("live-monitoring-patient-select", "value"),
)
def refresh_live_view(_n_intervals, patient_id):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate
    if not patient_id:
        return dbc.Alert("No active patients to monitor.", color="info")

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            vitals = client.get_latest_vitals(patient_id)
            vitals_history = client.get_vitals_history(patient_id, limit=50)
            prediction = client.get_latest_prediction(patient_id)
    except ApiError as exc:
        return dbc.Alert(f"Could not load live data: {exc.detail}", color="danger")

    prob = f"{prediction['sepsis_probability']:.1%}" if prediction else "--"
    risk = prediction["risk_level"] if prediction else None
    last_reading = format_timestamp(vitals["timestamp"]) if vitals else "--"

    kpi_row = dbc.Row(
        [
            dbc.Col(kpi_card("Last Reading", last_reading, vitals["source"] if vitals else "", "#a78bfa", "fa-solid fa-clock"), md=4, class_name="mb-3"),
            dbc.Col(kpi_card("Sepsis Probability", prob, "", "#38bdf8", "fa-solid fa-heart-pulse"), md=4, class_name="mb-3"),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([html.Div("Risk Level", className="icu-kpi-title mb-2"), risk_badge(risk)]),
                    class_name="icu-card h-100",
                ),
                md=4, class_name="mb-3",
            ),
        ]
    )
    chart = dcc.Graph(figure=build_vitals_figure(vitals_history))
    return html.Div([kpi_row, chart])
