import dash
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, ctx, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.components.cards import risk_badge
from dashboard.utils.formatting import format_timestamp

dash.register_page(__name__, path="/alerts", name="Alerts")

_RISK_LEVELS = ["Low", "Medium", "High", "Critical"]


def layout():
    return html.Div(
        [
            dcc.Interval(id="alerts-init", interval=200, max_intervals=1),
            dcc.Store(id="alerts-refresh-signal", data=0),
            html.Div(
                [
                    html.H2([html.I(className="fa-solid fa-bell"), "Alerts"]),
                    html.Div("Clinical alerts triggered by the sepsis prediction engine", className="icu-page-subtitle"),
                ],
                className="icu-page-header",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dcc.Dropdown(
                            id="alerts-risk-filter",
                            options=[{"label": r, "value": r} for r in _RISK_LEVELS],
                            placeholder="Filter by risk level",
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        dcc.Dropdown(
                            id="alerts-status-filter",
                            options=[{"label": "Unacknowledged", "value": "false"}, {"label": "Acknowledged", "value": "true"}],
                            placeholder="Filter by status",
                        ),
                        md=3,
                    ),
                ],
                class_name="mb-4",
            ),
            dbc.Spinner(html.Div(id="alerts-table"), color="info", size="sm"),
        ]
    )


@callback(
    Output("alerts-refresh-signal", "data"),
    Input({"type": "ack-alert-button", "index": ALL}, "n_clicks"),
    State("alerts-refresh-signal", "data"),
    prevent_initial_call=True,
)
def handle_acknowledge_click(_all_clicks, refresh_count):
    """Isolated from load_alerts below so that callback can stay a plain,
    directly-testable function -- dash.ctx (used here to find which of the N
    pattern-matched buttons was actually clicked) is only ever valid inside a
    real Dash callback dispatch."""
    triggered = ctx.triggered_id
    if not (isinstance(triggered, dict) and triggered.get("type") == "ack-alert-button"):
        raise dash.exceptions.PreventUpdate
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            client.acknowledge_alert(triggered["index"], auth.current_username())
    except ApiError:
        pass  # surfaced again via the refreshed table not showing it as acknowledged
    return (refresh_count or 0) + 1


@callback(
    Output("alerts-table", "children"),
    Input("alerts-init", "n_intervals"),
    Input("alerts-refresh-signal", "data"),
    Input("alerts-risk-filter", "value"),
    Input("alerts-status-filter", "value"),
)
def load_alerts(_n_intervals, _refresh_signal, risk_filter, status_filter):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    acknowledged = {"true": True, "false": False}.get(status_filter)
    try:
        with get_api_client() as client:
            alerts = client.list_alerts(risk_level=risk_filter, acknowledged=acknowledged, limit=200)
    except ApiError as exc:
        return dbc.Alert(f"Could not load alerts: {exc.detail}", color="danger")

    if not alerts:
        return dbc.Alert([html.I(className="fa-solid fa-circle-info me-2"), "No alerts match this filter."], color="info")

    rows = []
    for a in alerts:
        action_cell = (
            html.Span([html.I(className="fa-solid fa-check me-1"), f"Ack'd by {a['acknowledged_by']}"], className="text-muted small")
            if a["acknowledged"]
            else dbc.Button("Acknowledge", id={"type": "ack-alert-button", "index": a["id"]}, size="sm", color="warning")
        )
        rows.append(
            html.Tr(
                [
                    html.Td(risk_badge(a["risk_level"])),
                    html.Td(dcc.Link(a["patient_id"], href=f"/patients/{a['patient_id']}")),
                    html.Td(a["message"]),
                    html.Td(format_timestamp(a.get("created_at"))),
                    html.Td(action_cell),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([html.Th(h) for h in ["Risk", "Patient", "Message", "Time", "Action"]])),
            html.Tbody(rows),
        ],
        bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
    )
