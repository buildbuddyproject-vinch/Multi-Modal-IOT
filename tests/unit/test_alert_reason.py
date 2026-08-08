from src.alerts.reason import summarize_abnormal_vitals


def test_empty_or_missing_channels_returns_empty_string():
    assert summarize_abnormal_vitals(None) == ""
    assert summarize_abnormal_vitals({}) == ""


def test_all_normal_vitals_returns_empty_string():
    assert summarize_abnormal_vitals({"HR": 78.0, "Temp": 37.0, "O2Sat": 98.0, "SBP": 110.0}) == ""


def test_high_heart_rate_is_flagged_as_elevated():
    assert "Elevated Heart rate (118bpm)" in summarize_abnormal_vitals({"HR": 118.0})


def test_low_oxygen_saturation_is_flagged():
    assert "Low Oxygen saturation (88%)" in summarize_abnormal_vitals({"O2Sat": 88.0})


def test_fever_is_flagged_as_elevated_temperature():
    assert "Elevated Temperature" in summarize_abnormal_vitals({"Temp": 39.2})


def test_low_systolic_bp_is_flagged():
    assert "Low Systolic BP (82mmHg)" in summarize_abnormal_vitals({"SBP": 82.0})


def test_high_respiratory_rate_is_flagged_as_elevated():
    assert "Elevated Respiratory rate" in summarize_abnormal_vitals({"Resp": 28.0})


def test_result_is_capped_at_max_findings():
    channels = {"HR": 130.0, "Temp": 39.5, "SBP": 75.0, "MAP": 50.0, "Resp": 30.0}
    result = summarize_abnormal_vitals(channels, max_findings=2)
    assert len(result.split(", ")) == 2


def test_none_valued_channels_are_ignored_not_flagged():
    assert summarize_abnormal_vitals({"HR": None, "Temp": None}) == ""
