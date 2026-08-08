import numpy as np
import pytest

from src.models.evaluation.metrics import (
    compute_full_evaluation_report,
    compute_metrics_at_threshold,
    find_best_f1_threshold,
)


def test_metrics_at_threshold_perfect_classifier():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.1, 0.2, 0.8, 0.9])
    metrics = compute_metrics_at_threshold(y_true, y_prob, threshold=0.5)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall_sensitivity"] == pytest.approx(1.0)
    assert metrics["specificity"] == pytest.approx(1.0)
    assert metrics["f1_score"] == pytest.approx(1.0)
    assert metrics["confusion_matrix"] == {"tn": 2, "fp": 0, "fn": 0, "tp": 2}


def test_metrics_at_threshold_all_wrong():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.9, 0.8, 0.2, 0.1])
    metrics = compute_metrics_at_threshold(y_true, y_prob, threshold=0.5)
    assert metrics["precision"] == pytest.approx(0.0)
    assert metrics["recall_sensitivity"] == pytest.approx(0.0)
    assert metrics["confusion_matrix"] == {"tn": 0, "fp": 2, "fn": 2, "tp": 0}


def test_metrics_handle_no_positive_predictions_without_div_by_zero():
    y_true = np.array([0, 0, 1, 1])
    y_prob = np.array([0.01, 0.01, 0.01, 0.01])  # model predicts "no sepsis" for everyone
    metrics = compute_metrics_at_threshold(y_true, y_prob, threshold=0.5)
    assert metrics["precision"] == 0.0  # no positive predictions -> defined as 0, not NaN
    assert metrics["recall_sensitivity"] == 0.0
    assert metrics["specificity"] == 1.0


def test_find_best_f1_threshold_prefers_separating_threshold():
    y_true = np.array([0] * 50 + [1] * 50)
    y_prob = np.concatenate([np.full(50, 0.1), np.full(50, 0.9)])
    threshold = find_best_f1_threshold(y_true, y_prob)
    assert 0.1 < threshold <= 0.9


def test_full_evaluation_report_contains_expected_keys():
    rng = np.random.default_rng(0)
    y_true = rng.integers(0, 2, size=200)
    y_prob = np.clip(y_true * 0.6 + rng.normal(0, 0.2, size=200) + 0.2, 0, 1)
    report = compute_full_evaluation_report(y_true, y_prob)

    assert 0.0 <= report["auroc"] <= 1.0
    assert 0.0 <= report["auprc"] <= 1.0
    assert report["n_samples"] == 200
    assert "metrics_at_0.5" in report
    assert "metrics_at_best_f1_threshold" in report
    assert "classification_report_at_0.5" in report
    assert len(report["roc_curve"]["fpr"]) == len(report["roc_curve"]["tpr"])


def test_full_evaluation_report_auroc_close_to_one_for_near_perfect_separation():
    y_true = np.array([0] * 100 + [1] * 100)
    y_prob = np.concatenate([np.full(100, 0.05), np.full(100, 0.95)])
    report = compute_full_evaluation_report(y_true, y_prob)
    assert report["auroc"] == pytest.approx(1.0)
    assert report["metrics_at_0.5"]["f1_score"] == pytest.approx(1.0)
