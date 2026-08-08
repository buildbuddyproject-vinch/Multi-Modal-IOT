"""Plotly Dash entry point (Step 9). Run with `python scripts/run_dashboard.py`.

Every page is a pure client of the FastAPI backend (Step 8) via dashboard/api_client.py
-- no direct MongoDB access from here -- so nothing in this file changes when Phase 2
swaps simulated data for real IoT sensor data.
"""
import logging

import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, dcc, html
from flask import Flask, Response, abort, redirect

from dashboard import auth
from dashboard.api_client import ApiClient, ApiError
from dashboard.components.alert_toast import build_alert_toast
from dashboard.components.sidebar import build_sidebar
from dashboard.config import get_dashboard_settings
from src.utils.logging_config import configure_logging

settings = get_dashboard_settings()
configure_logging()
logger = logging.getLogger(__name__)

server = Flask(__name__)
server.secret_key = settings.dashboard_secret_key

app = dash.Dash(
    __name__,
    server=server,
    use_pages=True,
    external_stylesheets=[dbc.themes.CYBORG, dbc.icons.FONT_AWESOME],
    suppress_callback_exceptions=True,
    title="Sepsis ICU Monitor",
    update_title=None,
)

PUBLIC_PATHS = {"/login"}

app.layout = html.Div(
    [
        dcc.Location(id="url", refresh=False),
        dcc.Location(id="auth-redirect", refresh=True),
        html.Div(id="navbar-container"),
        html.Div(dash.page_container, className="app-main-col"),
        dcc.Interval(id="global-alert-poll", interval=8000),
        dcc.Store(id="seen-critical-alert-ids", storage_type="session", data=[]),
        html.Div(id="global-alert-toast-container", className="icu-toast-stack"),
    ],
    className="app-shell",
)


@app.callback(
    Output("url", "pathname", allow_duplicate=True),
    Output("auth-redirect", "pathname", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call="initial_duplicate",
)
def guard_route(pathname: str):
    """Bounces unauthenticated users to /login and logged-in users away from
    /login -- Dash pages have no built-in auth hook, so this callback is the
    single place that enforces it. Kept as its own callback (rather than
    combined with navbar rendering) because it both reads AND writes
    url.pathname -- bundling an unrelated Output into that same self-triggering
    callback made the whole thing unreliable to reason about and, in practice,
    to render correctly.

    The authenticated-user-hits-/login case redirects through auth-redirect
    (a hard browser navigation, see handle_login below) rather than the SPA
    "url" location -- that transition crosses an auth-state boundary within a
    live page, and Dash's client-side page_container router can lose the race
    against it, leaving the stale /login markup on screen even though the
    sidebar (a separate, simpler callback) already repaints correctly."""
    authenticated = auth.is_authenticated()
    if not authenticated and pathname not in PUBLIC_PATHS:
        return "/login", dash.no_update
    if authenticated and pathname == "/login":
        return dash.no_update, "/"
    return dash.no_update, dash.no_update


@app.callback(
    Output("navbar-container", "children"),
    Input("url", "pathname"),
)
def render_navbar(pathname: str):
    """Separate from guard_route above: this callback only ever reads
    url.pathname, never writes it, so it can't participate in that callback's
    redirect loop and always reflects the current session correctly."""
    return build_sidebar(pathname)


@app.callback(
    Output("auth-redirect", "pathname", allow_duplicate=True),
    Input("navbar-logout-button", "n_clicks"),
    prevent_initial_call=True,
)
def handle_logout(n_clicks):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    auth.log_out()
    return "/login"


_URGENT_RISK_LEVELS = {"High", "Critical"}


@app.callback(
    Output("global-alert-toast-container", "children"),
    Output("seen-critical-alert-ids", "data"),
    Input("global-alert-poll", "n_intervals"),
    State("seen-critical-alert-ids", "data"),
    State("global-alert-toast-container", "children"),
    State("url", "pathname"),
    prevent_initial_call=True,
)
def poll_critical_alerts(_n_intervals, seen_ids, existing_toasts, pathname):
    """Surfaces every new High/Critical alert as a red/orange popup toast,
    anywhere in the app, within one poll interval of the alert engine
    (Step 10) dispatching it -- so a clinician doesn't have to be on the
    Alerts page to notice a patient has deteriorated. Only ever *appends* to
    the existing toast list (rather than replacing it) so toasts already on
    screen aren't reset or force-reopened by the next poll."""
    if not auth.is_authenticated() or pathname == "/login":
        raise dash.exceptions.PreventUpdate

    seen_ids = seen_ids or []
    existing_toasts = existing_toasts or []
    try:
        with get_api_client() as client:
            alerts = client.list_alerts(acknowledged=False, limit=50)
    except ApiError:
        raise dash.exceptions.PreventUpdate

    new_alerts = [a for a in alerts if a["risk_level"] in _URGENT_RISK_LEVELS and a["id"] not in seen_ids]
    if not new_alerts:
        raise dash.exceptions.PreventUpdate

    new_toasts = [build_alert_toast(a) for a in new_alerts]
    updated_seen = (seen_ids + [a["id"] for a in new_alerts])[-300:]
    combined_toasts = (existing_toasts + new_toasts)[-6:]
    return combined_toasts, updated_seen


def get_api_client() -> ApiClient:
    """Per-request API client carrying the logged-in clinician's JWT."""
    return ApiClient(base_url=settings.api_base_url, token=auth.current_token())


@server.route("/downloads/patients/<patient_id>/report.pdf")
def download_patient_report(patient_id: str):
    """Plain Flask route (not a Dash callback) so a normal browser download
    navigation works -- it authenticates off the same signed session cookie
    every dashboard page uses (dashboard/auth.py), so the clinician's JWT
    never has to be exposed in a URL."""
    if not auth.is_authenticated():
        return redirect("/login")

    try:
        with get_api_client() as client:
            pdf_bytes = client.download_patient_report(patient_id)
    except ApiError as exc:
        abort(404 if exc.status_code == 404 else 502, description=exc.detail)

    return Response(
        pdf_bytes, mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{patient_id}_sepsis_report.pdf"'},
    )


__all__ = ["app", "server", "get_api_client", "ApiError"]
