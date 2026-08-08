import dash
import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html

from dashboard import auth
from dashboard.api_client import ApiError
from dashboard.components.cards import kpi_card, risk_badge
from dashboard.utils.formatting import build_prediction_trend_figure, build_shap_figure, build_vitals_figure, format_timestamp

dash.register_page(__name__, path_template="/patients/<patient_id>", name="Patient Detail")


def layout(patient_id: str = None, **_kwargs):
    return html.Div(
        [
            dcc.Interval(id="patient-detail-init", interval=200, max_intervals=1),
            dcc.Store(id="patient-detail-id", data=patient_id),
            html.Div(
                [
                    dcc.Link([html.I(className="fa-solid fa-arrow-left me-2"), "Back to patients"], href="/patients"),
                    html.A(
                        [html.I(className="fa-solid fa-file-pdf me-2"), "Download PDF Report"],
                        href=f"/downloads/patients/{patient_id}/report.pdf",
                        className="btn btn-info btn-sm",
                        target="_blank",
                    ),
                ],
                className="d-flex justify-content-between align-items-center mb-3",
            ),
            dbc.Spinner(html.Div(id="patient-detail-header"), color="info", size="sm"),
            dbc.Tabs(
                [
                    dbc.Tab(html.Div(id="patient-detail-vitals-tab", className="pt-3"),
                             label="Vitals History", tab_id="vitals", label_class_name="d-flex align-items-center"),
                    dbc.Tab(html.Div(id="patient-detail-prediction-tab", className="pt-3"),
                             label="Prediction Trend", tab_id="prediction"),
                    dbc.Tab(html.Div(id="patient-detail-shap-tab", className="pt-3"),
                             label="Explainability (SHAP)", tab_id="shap"),
                ],
                class_name="mt-2",
            ),
        ]
    )


@callback(
    Output("patient-detail-header", "children"),
    Output("patient-detail-vitals-tab", "children"),
    Output("patient-detail-prediction-tab", "children"),
    Output("patient-detail-shap-tab", "children"),
    Input("patient-detail-init", "n_intervals"),
    State("patient-detail-id", "data"),
)
def load_patient_detail(_n_intervals, patient_id):
    if not auth.is_authenticated():
        raise dash.exceptions.PreventUpdate

    from dashboard.app import get_api_client

    try:
        with get_api_client() as client:
            patient = client.get_patient(patient_id)
            vitals_history = client.get_vitals_history(patient_id, limit=1000)
            prediction_history = client.get_prediction_history(patient_id, limit=200)
            latest_prediction = prediction_history[0] if prediction_history else None
            shap_explanation = client.get_shap_by_prediction(latest_prediction["id"]) if latest_prediction else None
    except ApiError as exc:
        error = dbc.Alert(f"Could not load patient '{patient_id}': {exc.detail}", color="danger")
        return error, "", "", ""

    header = _build_header(patient, latest_prediction)
    vitals_tab = dcc.Graph(figure=build_vitals_figure(vitals_history))
    prediction_tab = dcc.Graph(figure=build_prediction_trend_figure(prediction_history))
    shap_tab = _build_shap_tab(shap_explanation)

    return header, vitals_tab, prediction_tab, shap_tab


def _build_header(patient: dict, latest_prediction: dict | None) -> dbc.Row:
    risk = latest_prediction["risk_level"] if latest_prediction else None
    prob = f"{latest_prediction['sepsis_probability']:.1%}" if latest_prediction else "--"
    updated = format_timestamp(latest_prediction.get("created_at")) if latest_prediction else "--"

    return dbc.Row(
        [
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H3([html.I(className="fa-solid fa-user me-2 text-info"), patient["patient_id"]]),
                            html.P(
                                f"Age {patient.get('age', '--')}  ·  Sex {patient.get('sex', '--')}  ·  "
                                f"Unit {patient.get('unit_admitted', '--')}  ·  Status {patient['current_status']}",
                                className="text-muted mb-0",
                            ),
                        ]
                    ),
                    class_name="icu-card h-100",
                ),
                md=6, class_name="mb-3",
            ),
            dbc.Col(kpi_card("Sepsis Probability", prob, f"Updated {updated}", "#38bdf8", "fa-solid fa-heart-pulse"), md=3, class_name="mb-3"),
            dbc.Col(
                dbc.Card(
                    dbc.CardBody([html.Div("Risk Level", className="icu-kpi-title mb-2"), risk_badge(risk)]),
                    class_name="icu-card h-100",
                ),
                md=3, class_name="mb-3",
            ),
        ]
    )


def _build_shap_tab(shap_explanation: dict | None):
    if shap_explanation is None:
        return dbc.Alert(
            [html.I(className="fa-solid fa-circle-info me-2"), "No SHAP explanation available yet for this patient's latest prediction."],
            color="info",
        )

    features_table = dbc.Table(
        [
            html.Thead(html.Tr([html.Th("Channel"), html.Th("Observed Value"), html.Th("Contribution")])),
            html.Tbody(
                [
                    html.Tr([html.Td(f["feature"]), html.Td(f"{f['value']:.2f}"), html.Td(f"{f['contribution']:+.4f}")])
                    for f in shap_explanation.get("top_contributing_features", [])
                ]
            ),
        ],
        bordered=False, hover=True, responsive=True, class_name="icu-table icu-table-card",
    )
    return html.Div(
        [
            dcc.Graph(figure=build_shap_figure(shap_explanation["shap_values"])),
            html.Div([html.I(className="fa-solid fa-list-ol"), "Top Contributing Channels"], className="icu-section-title mt-2"),
            features_table,
        ]
    )
