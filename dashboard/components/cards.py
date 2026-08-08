import dash_bootstrap_components as dbc
from dash import html


def kpi_card(title: str, value, subtitle: str = "", color: str = "#38bdf8", icon: str = "fa-solid fa-chart-line") -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(className="icu-kpi-accent", style={"backgroundColor": color}),
                html.Div(html.I(className=icon), className="icu-kpi-icon",
                          style={"backgroundColor": f"{color}22", "color": color}),
                html.Div(title, className="icu-kpi-title"),
                html.Div(str(value), className="icu-kpi-value", style={"color": color}),
                html.Div(subtitle, className="text-muted small mt-1") if subtitle else None,
            ]
        ),
        class_name="icu-card icu-kpi-card h-100",
    )


def risk_badge(risk_level: str) -> html.Span:
    from dashboard.theme import risk_color

    color = risk_color(risk_level)
    return html.Span(
        [html.Span(className="icu-risk-dot", style={"backgroundColor": color, "color": color}), risk_level or "Unknown"],
        className="icu-risk-badge",
        style={"backgroundColor": f"{color}1f", "color": color},
    )
