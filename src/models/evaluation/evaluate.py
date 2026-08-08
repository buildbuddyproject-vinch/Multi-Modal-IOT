"""Runs the trained model against the held-out test split and saves every
evaluation artifact (metrics.json, classification_report.txt, ROC curve,
confusion matrix, training curves)."""
import json
import logging
from pathlib import Path

import numpy as np
import keras

from src.models.evaluation.metrics import compute_full_evaluation_report
from src.models.evaluation.plots import plot_confusion_matrix, plot_roc_curve, plot_training_curves

logger = logging.getLogger(__name__)


def evaluate_model(
    model: keras.Model,
    test_npz: Path,
    output_dir: Path,
    history: dict | None = None,
) -> dict:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with np.load(test_npz) as data:
        X_test, y_test = data["X"], data["y"]

    logger.info("Evaluating on %d test windows (positive rate %.4f)", len(y_test), y_test.mean())
    y_prob = model.predict(X_test, verbose=0).ravel()

    report = compute_full_evaluation_report(y_test, y_prob)

    (output_dir / "classification_report.txt").write_text(report.pop("classification_report_at_0.5"))

    roc_curve_data = report.pop("roc_curve")
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    logger.info(
        "AUROC=%.4f AUPRC=%.4f | @0.5: precision=%.4f recall=%.4f f1=%.4f | @best-F1(t=%.3f): precision=%.4f recall=%.4f f1=%.4f",
        report["auroc"], report["auprc"],
        report["metrics_at_0.5"]["precision"], report["metrics_at_0.5"]["recall_sensitivity"], report["metrics_at_0.5"]["f1_score"],
        report["metrics_at_best_f1_threshold"]["threshold"],
        report["metrics_at_best_f1_threshold"]["precision"], report["metrics_at_best_f1_threshold"]["recall_sensitivity"], report["metrics_at_best_f1_threshold"]["f1_score"],
    )

    plot_roc_curve(y_test, y_prob, report["auroc"], output_dir / "roc_curve.png")
    plot_confusion_matrix(report["metrics_at_0.5"]["confusion_matrix"], output_dir / "confusion_matrix_at_0.5.png", threshold=0.5)
    plot_confusion_matrix(
        report["metrics_at_best_f1_threshold"]["confusion_matrix"],
        output_dir / "confusion_matrix_at_best_f1.png",
        threshold=report["metrics_at_best_f1_threshold"]["threshold"],
    )
    if history:
        plot_training_curves(history, output_dir / "training_curves.png")

    report["roc_curve"] = roc_curve_data  # restore for the return value / callers that want it
    return report
