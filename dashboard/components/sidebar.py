"""Left navigation sidebar (Step 9, restyled): the single place session state
(auth.py) is read to decide what nav is visible -- returns an empty shell for
unauthenticated visitors so the login page renders full-width."""
import dash_bootstrap_components as dbc
from dash import html

from dashboard import auth

_NAV_ITEMS = [
    ("Dashboard", "/", "fa-solid fa-gauge-high"),
    ("Patients", "/patients", "fa-solid fa-user-injured"),
    ("Admit Patient", "/admit-patient", "fa-solid fa-user-plus"),
    ("Live Monitoring", "/live-monitoring", "fa-solid fa-wave-square"),
    ("Alerts", "/alerts", "fa-solid fa-bell"),
]


def build_sidebar(current_path: str = "/") -> html.Div:
    if not auth.is_authenticated():
        return html.Div(className="d-none")

    nav_items = list(_NAV_ITEMS)
    if auth.is_admin():
        nav_items = nav_items + [("Admin", "/admin", "fa-solid fa-shield-halved")]

    def _is_active(href: str) -> bool:
        if href == "/patients":
            return current_path == href or current_path.startswith("/patients/")
        return current_path == href

    links = [
        html.A(
            [html.I(className=icon), html.Span(label)],
            href=href,
            className="icu-nav-link" + (" active" if _is_active(href) else ""),
        )
        for label, href, icon in nav_items
    ]

    username = auth.current_username() or "?"
    initials = "".join(part[0] for part in username.replace(".", " ").replace("_", " ").split()[:2]).upper() or username[:2].upper()

    return html.Div(
        [
            html.Div(
                [
                    html.Div("🩺", className="icu-sidebar-brand-icon"),
                    html.Div(
                        [
                            html.Div("Sepsis ICU Monitor", className="icu-sidebar-brand-title"),
                            html.Div("Multi-Modal Prediction", className="icu-sidebar-brand-subtitle"),
                        ],
                        className="icu-sidebar-brand-text",
                    ),
                ],
                className="icu-sidebar-brand",
            ),
            html.Div(links, className="icu-nav"),
            html.Div(
                [
                    html.Div(
                        [
                            html.Div(initials, className="icu-user-avatar"),
                            html.Div(
                                [
                                    html.Div(auth.current_username(), className="icu-user-name"),
                                    html.Div(auth.current_role(), className="icu-user-role"),
                                ],
                                className="icu-user-meta",
                            ),
                        ],
                        className="icu-user-chip",
                    ),
                    dbc.Button(
                        [html.I(className="fa-solid fa-arrow-right-from-bracket me-2"), "Log out"],
                        id="navbar-logout-button", size="sm", color="secondary", outline=True, class_name="w-100",
                    ),
                ],
                className="icu-sidebar-footer",
            ),
        ],
        className="icu-sidebar",
        id="app-navbar",
    )
