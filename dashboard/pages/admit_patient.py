"""Step 12+ "Admit Patient" page: the only way a clinician/admin account gets
a patient into their own private view (src/api/routes/patients.py's
per-account ownership model) short of the seed script or the live MQTT
pipeline, both of which are owned by whichever account started them. Without
this page a freshly-created account would have no way to ever see a patient."""
import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError

dash.register_page(__name__, path="/admit-patient", name="Admit Patient")

_SOURCE_OPTIONS = [
    {"label": "Live / manually admitted", "value": "live"},
    {"label": "PhysioNet 2019", "value": "physionet_2019"},
    {"label": "MIMIC-IV (demo)", "value": "mimic_iv_demo"},
]


def layout():
    return html.Div(
        [
            html.Div(
                [
                    html.H2([html.I(className="fa-solid fa-user-plus"), "Admit Patient"]),
                    html.Div(
                        "Every patient belongs to your account only — other clinicians and admins won't see this patient.",
                        className="icu-page-subtitle",
                    ),
                ],
                className="icu-page-header",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        dbc.Row(
                            [
                                dbc.Col([dbc.Label("Patient ID"), dbc.Input(id="admit-patient-id", placeholder="e.g. p_jane_doe")], md=6, class_name="mb-3"),
                                dbc.Col([
                                    dbc.Label("Source"),
                                    dcc.Dropdown(id="admit-patient-source", options=_SOURCE_OPTIONS, value="live", clearable=False),
                                ], md=6, class_name="mb-3"),
                            ]
                        ),
                        dbc.Row(
                            [
                                dbc.Col([dbc.Label("Age"), dbc.Input(id="admit-patient-age", type="number", min=0, max=130)], md=4, class_name="mb-3"),
                                dbc.Col([
                                    dbc.Label("Sex"),
                                    dcc.Dropdown(id="admit-patient-sex", options=[{"label": "Male", "value": "M"}, {"label": "Female", "value": "F"}], clearable=True),
                                ], md=4, class_name="mb-3"),
                                dbc.Col([dbc.Label("Unit Admitted"), dbc.Input(id="admit-patient-unit", placeholder="e.g. MICU")], md=4, class_name="mb-3"),
                            ]
                        ),
                        dbc.Button(
                            [html.I(className="fa-solid fa-user-plus me-2"), "Admit Patient"],
                            id="admit-patient-submit-button", color="info",
                        ),
                        html.Div(id="admit-patient-feedback", className="mt-3"),
                    ]
                ),
                class_name="icu-card",
            ),
        ]
    )


@callback(
    Output("admit-patient-feedback", "children"),
    Output("admit-patient-id", "value"),
    Input("admit-patient-submit-button", "n_clicks"),
    State("admit-patient-id", "value"),
    State("admit-patient-source", "value"),
    State("admit-patient-age", "value"),
    State("admit-patient-sex", "value"),
    State("admit-patient-unit", "value"),
    prevent_initial_call=True,
)
def handle_admit_patient(n_clicks, patient_id, source_dataset, age, sex, unit_admitted):
    if not n_clicks or not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate
    if not patient_id or not patient_id.strip():
        return dbc.Alert("Patient ID is required.", color="warning"), dash.no_update

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            patient = client.create_patient(patient_id.strip(), source_dataset, age=age, sex=sex, unit_admitted=unit_admitted)
    except ApiError as exc:
        detail = "A patient with that ID already exists." if exc.status_code == 409 else exc.detail
        return dbc.Alert(f"Could not admit patient: {detail}", color="danger"), dash.no_update

    feedback = dbc.Alert(
        [
            html.I(className="fa-solid fa-circle-check me-2"),
            f"Admitted patient '{patient['patient_id']}'. ",
            dcc.Link("View patient →", href=f"/patients/{patient['patient_id']}", className="alert-link"),
        ],
        color="success",
    )
    return feedback, ""
