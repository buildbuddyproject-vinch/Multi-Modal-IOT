from src.models.inference.risk import BEST_F1_THRESHOLD, predicted_label, probability_to_risk_level


def test_threshold_loaded_from_real_metrics_file():
    assert 0.0 < BEST_F1_THRESHOLD < 1.0


def test_predicted_label_matches_threshold():
    assert predicted_label(BEST_F1_THRESHOLD - 0.001) == 0
    assert predicted_label(BEST_F1_THRESHOLD) == 1
    assert predicted_label(BEST_F1_THRESHOLD + 0.001) == 1


def test_risk_level_buckets_are_ordered_and_exhaustive():
    assert probability_to_risk_level(0.01) == "Low"
    assert probability_to_risk_level(0.15) == "Medium"
    assert probability_to_risk_level(min(BEST_F1_THRESHOLD + 0.01, 0.49)) == "High"
    assert probability_to_risk_level(0.9) == "Critical"


def test_risk_level_boundaries_are_inclusive_on_the_upper_bucket():
    assert probability_to_risk_level(0.5) == "Critical"
    assert probability_to_risk_level(0.10) == "Medium"
