import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from dashboard import auth
from dashboard.api_client import ApiClient, ApiError
from dashboard.config import get_dashboard_settings

dash.register_page(__name__, path="/login", name="Login")


def layout():
    return html.Div(
        dbc.Card(
            dbc.CardBody(
                [
                    html.Div("🩺", className="icu-login-icon"),
                    html.Div("Sepsis ICU Monitor", className="icu-login-title"),
                    html.Div("Multi-Modal IoT & Deep Learning Sepsis Prediction", className="icu-login-subtitle"),
                    dbc.Label("Username", class_name="form-label"),
                    dbc.Input(id="login-username", type="text", placeholder="e.g. dr_smith", class_name="mb-3"),
                    dbc.Label("Password", class_name="form-label"),
                    dbc.Input(id="login-password", type="password", placeholder="••••••••", class_name="mb-3", n_submit=0),
                    dbc.Button(
                        [html.I(className="fa-solid fa-arrow-right-to-bracket me-2"), "Log in"],
                        id="login-submit-button", color="info", class_name="w-100 mb-2",
                    ),
                    html.Div(id="login-error", className="text-danger small text-center"),
                ]
            ),
            class_name="icu-login-card",
        ),
        className="icu-login-page",
    )


@callback(
    Output("auth-redirect", "pathname", allow_duplicate=True),
    Output("login-error", "children"),
    Input("login-submit-button", "n_clicks"),
    Input("login-password", "n_submit"),
    State("login-username", "value"),
    State("login-password", "value"),
    prevent_initial_call=True,
)
def handle_login(n_clicks, n_submit, username, password):
    """Redirects through the "auth-redirect" dcc.Location (refresh=True, see
    dashboard/app.py) rather than the SPA "url" location -- a hard browser
    navigation guarantees the whole app re-boots against the freshly-set
    session cookie, instead of racing Dash's client-side page_container
    router across the auth-state transition (the cause of the stale
    login-page-behind-authenticated-sidebar glitch)."""
    if not username or not password:
        return dash.no_update, "Enter both a username and password."

    settings = get_dashboard_settings()
    try:
        with ApiClient(base_url=settings.api_base_url) as client:
            token_payload = client.login(username, password)
    except ApiError as exc:
        return dash.no_update, "Invalid username or password." if exc.status_code == 401 else f"Login failed: {exc.detail}"

    auth.log_in(token_payload["access_token"], token_payload["username"], token_payload["role"])
    return "/", ""
