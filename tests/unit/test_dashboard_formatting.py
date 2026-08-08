from dashboard.utils.formatting import (
    build_prediction_trend_figure,
    build_shap_figure,
    build_vitals_figure,
    format_timestamp,
    summarize_alerts,
    summarize_patients,
)


def test_format_timestamp_handles_none():
    assert format_timestamp(None) == "--"


def test_format_timestamp_parses_iso_string():
    assert format_timestamp("2026-08-05T10:30:00+00:00") == "2026-08-05 10:30:00 UTC"


def test_summarize_alerts_counts_by_risk_level():
    alerts = [{"risk_level": "Critical"}, {"risk_level": "Critical"}, {"risk_level": "Low"}]
    counts = summarize_alerts(alerts)
    assert counts == {"Low": 1, "Medium": 0, "High": 0, "Critical": 2}


def test_summarize_patients_counts_by_status():
    patients = [{"current_status": "active"}, {"current_status": "active"}, {"current_status": "discharged"}]
    counts = summarize_patients(patients)
    assert counts == {"active": 2, "discharged": 1, "deceased": 0}


def test_build_vitals_figure_empty_history_shows_placeholder():
    fig = build_vitals_figure([])
    assert len(fig.data) == 0
    assert fig.layout.annotations[0].text == "No data yet"


def test_build_vitals_figure_plots_channels_with_data_only():
    history = [
        {"timestamp": "2026-08-05T10:00:00", "channels": {"HR": 90, "O2Sat": None}},
        {"timestamp": "2026-08-05T11:00:00", "channels": {"HR": 95, "O2Sat": None}},
    ]
    fig = build_vitals_figure(history, channels=["HR", "O2Sat"])
    names = [trace.name for trace in fig.data]
    assert names == ["HR"]
    assert list(fig.data[0].y) == [90, 95]


def test_build_vitals_figure_sorts_by_timestamp():
    history = [
        {"timestamp": "2026-08-05T11:00:00", "channels": {"HR": 95}},
        {"timestamp": "2026-08-05T10:00:00", "channels": {"HR": 90}},
    ]
    fig = build_vitals_figure(history, channels=["HR"])
    assert list(fig.data[0].y) == [90, 95]


def test_build_prediction_trend_figure_empty():
    fig = build_prediction_trend_figure([])
    assert len(fig.data) == 0


def test_build_prediction_trend_figure_orders_and_colors():
    preds = [
        {"created_at": "2026-08-05T11:00:00", "sepsis_probability": 0.8, "risk_level": "Critical"},
        {"created_at": "2026-08-05T10:00:00", "sepsis_probability": 0.1, "risk_level": "Low"},
    ]
    fig = build_prediction_trend_figure(preds)
    assert list(fig.data[0].y) == [0.1, 0.8]


def test_build_shap_figure_ranks_by_absolute_contribution_top_n():
    shap_values = {"Temp": 0.05, "Lactate": 0.3, "HR": -0.02, "WBC": 0.15}
    fig = build_shap_figure(shap_values, top_n=2)
    # largest at bottom-to-top means last element (top of chart) is the biggest
    assert list(fig.data[0].y) == ["WBC", "Lactate"]


def test_build_shap_figure_empty():
    fig = build_shap_figure({})
    assert len(fig.data) == 0
