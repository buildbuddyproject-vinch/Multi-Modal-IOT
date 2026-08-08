"""Binary classification evaluation metrics for the trained sepsis model.

Both a fixed 0.5 threshold and the best-F1 threshold are reported: sepsis onset is
rare (~1.9% of windows, Step 3 EDA), so a 0.5 cutoff is not necessarily where
precision/recall trade off best -- reporting both gives an honest picture rather
than hiding behind whichever threshold looks better.
"""
import numpy as np
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    classification_report,
    precision_recall_curve,
    roc_auc_score,
    roc_curve,
)


def compute_metrics_at_threshold(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # sensitivity
    specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / (tp + tn + fp + fn)

    return {
        "threshold": float(threshold),
        "precision": float(precision),
        "recall_sensitivity": float(recall),
        "specificity": float(specificity),
        "f1_score": float(f1),
        "accuracy": float(accuracy),
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
    }


def find_best_f1_threshold(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    f1_scores = np.divide(
        2 * precisions * recalls, precisions + recalls,
        out=np.zeros_like(precisions), where=(precisions + recalls) > 0,
    )
    best_idx = int(np.argmax(f1_scores[:-1])) if len(thresholds) > 0 else 0
    return float(thresholds[best_idx]) if len(thresholds) > 0 else 0.5


def compute_full_evaluation_report(y_true: np.ndarray, y_prob: np.ndarray) -> dict:
    """AUROC/AUPRC (threshold-independent) plus metrics at threshold=0.5 and at the
    best-F1 threshold, plus the ROC curve data and a text classification report."""
    y_true = np.asarray(y_true).ravel()
    y_prob = np.asarray(y_prob).ravel()

    auroc = roc_auc_score(y_true, y_prob)
    auprc = average_precision_score(y_true, y_prob)
    fpr, tpr, roc_thresholds = roc_curve(y_true, y_prob)

    best_threshold = find_best_f1_threshold(y_true, y_prob)

    return {
        "auroc": float(auroc),
        "auprc": float(auprc),
        "n_samples": int(len(y_true)),
        "positive_rate": float(y_true.mean()),
        "metrics_at_0.5": compute_metrics_at_threshold(y_true, y_prob, 0.5),
        "metrics_at_best_f1_threshold": compute_metrics_at_threshold(y_true, y_prob, best_threshold),
        "classification_report_at_0.5": classification_report(y_true, (y_prob >= 0.5).astype(int), digits=4, zero_division=0),
        "roc_curve": {"fpr": fpr.tolist(), "tpr": tpr.tolist(), "thresholds": roc_thresholds.tolist()},
    }
