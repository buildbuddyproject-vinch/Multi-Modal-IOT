import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.utils.formatting import format_timestamp

dash.register_page(__name__, path="/admin", name="Admin")


def layout():
    return html.Div(
        [
            dcc.Interval(id="admin-init", interval=200, max_intervals=1),
            html.Div(
                [
                    html.H2([html.I(className="fa-solid fa-shield-halved"), "Admin"]),
                    html.Div("System health, user accounts, and the full audit trail", className="icu-page-subtitle"),
                ],
                className="icu-page-header",
            ),
            dbc.Spinner(html.Div(id="admin-body"), color="info", size="sm"),
        ]
    )


@callback(Output("admin-body", "children"), Input("admin-init", "n_intervals"))
def render_admin_page(_n_intervals):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate
    if not auth.is_admin():
        return dbc.Alert("This page is restricted to admin accounts.", color="danger")

    return html.Div(
        [
            html.Div([html.I(className="fa-solid fa-heart-pulse"), "System Health"], className="icu-section-title"),
            html.Div(id="admin-health-status", className="mb-4"),
            html.Div([html.I(className="fa-solid fa-users"), "Users"], className="icu-section-title"),
            html.Div(id="admin-users-table", className="mb-4"),
            html.Div([html.I(className="fa-solid fa-user-plus"), "Create User"], className="icu-section-title"),
            dbc.Row(
                [
                    dbc.Col(dbc.Input(id="admin-new-username", placeholder="Username"), md=3),
                    dbc.Col(dbc.Input(id="admin-new-password", placeholder="Password (min 8 chars)", type="password"), md=3),
                    dbc.Col(
                        dcc.Dropdown(
                            id="admin-new-role",
                            options=[{"label": "Clinician", "value": "clinician"}, {"label": "Admin", "value": "admin"}],
                            value="clinician", clearable=False,
                        ),
                        md=2,
                    ),
                    dbc.Col(dbc.Button("Create", id="admin-create-user-button", color="info"), md=2),
                ],
                class_name="g-2 align-items-center mb-2",
            ),
            html.Div(id="admin-create-user-feedback", className="small mb-4"),
            html.Div([html.I(className="fa-solid fa-clipboard-list"), "Audit Log"], className="icu-section-title"),
            html.Div(id="admin-audit-log-table"),
        ]
    )


@callback(
    Output("admin-health-status", "children"),
    Output("admin-users-table", "children"),
    Output("admin-audit-log-table", "children"),
    Input("admin-init", "n_intervals"),
    Input("admin-create-user-feedback", "children"),
)
def load_admin_data(_n_intervals, _feedback):
    if not (auth.is_authenticated() and auth.is_admin()):
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            health = client.health()
            users = client.list_users()
            audit_logs = client.list_audit_logs(limit=100)
    except ApiError as exc:
        error = dbc.Alert(f"Could not load admin data: {exc.detail}", color="danger")
        return error, "", ""

    health_badge = dbc.Badge(
        health["status"].upper(), color="success" if health["status"] == "ok" else "danger", class_name="me-2"
    )
    health_view = html.Div(
        [health_badge, f"MongoDB connected: {health['mongo_connected']} | API version: {health['version']}"],
        className="text-muted",
    )

    rows = [html.Tr([html.Td(u["username"]), html.Td(dbc.Badge(u["role"], color="secondary")), html.Td(u.get("last_login") or "never")]) for u in users]
    users_table = dbc.Table(
        [html.Thead(html.Tr([html.Th("Username"), html.Th("Role"), html.Th("Last Login")])), html.Tbody(rows)],
        bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
    )

    audit_table = _build_audit_log_table(audit_logs)
    return health_view, users_table, audit_table


def _build_audit_log_table(audit_logs: list[dict]) -> dbc.Table:
    if not audit_logs:
        return dbc.Alert([html.I(className="fa-solid fa-circle-info me-2"), "No audit log entries yet."], color="info")

    _ACTION_COLORS = {
        "login": "info", "prediction_run": "secondary",
        "alert_dispatched": "warning", "alert_acknowledged": "success",
    }
    rows = [
        html.Tr([
            html.Td(dbc.Badge(log["action"], color=_ACTION_COLORS.get(log["action"], "secondary"))),
            html.Td(log["actor"]),
            html.Td(f"{log.get('target_type') or ''} {log.get('target_id') or ''}".strip()),
            html.Td(format_timestamp(log.get("timestamp"))),
        ])
        for log in audit_logs
    ]
    return dbc.Table(
        [html.Thead(html.Tr([html.Th("Action"), html.Th("Actor"), html.Th("Target"), html.Th("Time")])), html.Tbody(rows)],
        bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
    )


@callback(
    Output("admin-create-user-feedback", "children"),
    Input("admin-create-user-button", "n_clicks"),
    State("admin-new-username", "value"),
    State("admin-new-password", "value"),
    State("admin-new-role", "value"),
    prevent_initial_call=True,
)
def create_user(n_clicks, username, password, role):
    if not n_clicks or not (auth.is_authenticated() and auth.is_admin()):
        raise dash.exceptions.PreventUpdate
    if not username or not password:
        return dbc.Alert("Username and password are required.", color="warning")

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            client.register_user(username, password, role)
    except ApiError as exc:
        return dbc.Alert(f"Could not create user: {exc.detail}", color="danger")

    return dbc.Alert(f"Created user '{username}' ({role}).", color="success")
