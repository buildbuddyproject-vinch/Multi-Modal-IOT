import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.components.cards import risk_badge

dash.register_page(__name__, path="/patients", name="Patients")


def layout():
    return html.Div(
        [
            dcc.Interval(id="patients-init", interval=200, max_intervals=1),
            html.Div(
                [
                    html.Div(
                        [
                            html.H2([html.I(className="fa-solid fa-user-injured"), "Patient Overview"]),
                            html.Div("Patients you've admitted and their latest risk assessment", className="icu-page-subtitle"),
                        ]
                    ),
                    dcc.Link(
                        dbc.Button([html.I(className="fa-solid fa-user-plus me-2"), "Admit Patient"], color="info", size="sm"),
                        href="/admit-patient",
                    ),
                ],
                className="icu-page-header d-flex justify-content-between align-items-start",
            ),
            dbc.Spinner(html.Div(id="patients-table"), color="info", size="sm"),
        ]
    )


@callback(Output("patients-table", "children"), Input("patients-init", "n_intervals"))
def load_patients(_n_intervals):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            patients = client.list_patients(limit=500)
            latest_predictions = {}
            for patient in patients:
                pred = client.get_latest_prediction(patient["patient_id"])
                latest_predictions[patient["patient_id"]] = pred
    except ApiError as exc:
        return dbc.Alert(f"Could not load patients: {exc.detail}", color="danger")

    if not patients:
        return dbc.Alert(
            [html.I(className="fa-solid fa-circle-info me-2"), "No patients yet. ",
             dcc.Link("Admit your first patient →", href="/admit-patient", className="alert-link")],
            color="info",
        )

    rows = []
    for p in sorted(patients, key=lambda p: p["patient_id"]):
        pred = latest_predictions.get(p["patient_id"])
        risk_cell = risk_badge(pred["risk_level"]) if pred else html.Span("--", className="text-muted")
        prob_cell = f"{pred['sepsis_probability']:.2f}" if pred else "--"
        rows.append(
            html.Tr(
                [
                    html.Td(dcc.Link([html.I(className="fa-solid fa-arrow-up-right-from-square me-2 small"), p["patient_id"]], href=f"/patients/{p['patient_id']}")),
                    html.Td(p.get("age", "--")),
                    html.Td(p.get("sex", "--")),
                    html.Td(p.get("unit_admitted", "--")),
                    html.Td(dbc.Badge(p["current_status"], color="secondary")),
                    html.Td(risk_cell),
                    html.Td(prob_cell),
                ]
            )
        )

    return dbc.Table(
        [
            html.Thead(html.Tr([html.Th(h) for h in ["Patient ID", "Age", "Sex", "Unit", "Status", "Latest Risk", "Probability"]])),
            html.Tbody(rows),
        ],
        bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
    )
