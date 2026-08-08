from src.reports.patient_report_pdf import build_patient_report_pdf

_PATIENT = {"patient_id": "p1", "source_dataset": "physionet_2019", "age": 66, "sex": "M",
            "unit_admitted": "ICU-3", "current_status": "active", "admission_time": "2026-08-05T08:00:00+00:00"}
_VITALS = [
    {"timestamp": "2026-08-05T10:00:00+00:00", "source": "physionet_sim",
     "channels": {"HR": 110.0, "O2Sat": 92.0, "Temp": 38.9, "SBP": 88.0, "MAP": 60.0, "Resp": 26.0}},
    {"timestamp": "2026-08-05T09:00:00+00:00", "source": "physionet_sim",
     "channels": {"HR": 105.0, "O2Sat": 94.0, "Temp": 38.5, "SBP": 90.0, "MAP": 62.0, "Resp": 24.0}},
]
_PREDICTIONS = [
    {"created_at": "2026-08-05T10:00:00+00:00", "sepsis_probability": 0.83, "risk_level": "Critical", "model_version": "hybrid_cnn_bilstm_transformer_v1"},
]
_SHAP = {"top_contributing_features": [
    {"feature": "Lactate", "value": 4.2, "contribution": 0.31},
    {"feature": "HR", "value": 110.0, "contribution": 0.12},
]}
_ALERTS = [
    {"created_at": "2026-08-05T10:00:05+00:00", "risk_level": "Critical", "message": "Critical sepsis risk detected", "acknowledged": False},
]


def test_report_produces_valid_pdf_bytes():
    pdf_bytes = build_patient_report_pdf(_PATIENT, _VITALS, _PREDICTIONS, _SHAP, _ALERTS)
    assert pdf_bytes.startswith(b"%PDF")
    assert pdf_bytes.endswith(b"%%EOF\n") or b"%%EOF" in pdf_bytes[-64:]
    assert len(pdf_bytes) > 1000


def test_report_handles_patient_with_no_data_at_all():
    pdf_bytes = build_patient_report_pdf({"patient_id": "empty_patient", "current_status": "active"}, [], [], None, [])
    assert pdf_bytes.startswith(b"%PDF")


def test_report_handles_missing_shap_explanation():
    pdf_bytes = build_patient_report_pdf(_PATIENT, _VITALS, _PREDICTIONS, None, _ALERTS)
    assert pdf_bytes.startswith(b"%PDF")


def test_report_is_deterministic_in_size_for_same_input_shape():
    """Not a byte-for-byte snapshot (reportlab embeds a generation timestamp in
    the PDF's own metadata) -- just a sanity check that rendering the same
    logical content twice doesn't wildly change output size."""
    first = build_patient_report_pdf(_PATIENT, _VITALS, _PREDICTIONS, _SHAP, _ALERTS)
    second = build_patient_report_pdf(_PATIENT, _VITALS, _PREDICTIONS, _SHAP, _ALERTS)
    assert abs(len(first) - len(second)) < 50
