"""Plot generation for Step 5 evaluation artifacts."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from sklearn.metrics import roc_curve

sns.set_theme(style="whitegrid")


def _save(fig: plt.Figure, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return output_path


def plot_roc_curve(y_true: np.ndarray, y_prob: np.ndarray, auroc: float, output_path: Path) -> Path:
    fpr, tpr, _ = roc_curve(y_true, y_prob)
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot(fpr, tpr, label=f"Model (AUROC = {auroc:.3f})", color="#4C72B0", linewidth=2)
    ax.plot([0, 1], [0, 1], linestyle="--", color="gray", label="Chance")
    ax.set_xlabel("False Positive Rate (1 - Specificity)")
    ax.set_ylabel("True Positive Rate (Sensitivity)")
    ax.set_title("ROC Curve")
    ax.legend(loc="lower right")
    return _save(fig, output_path)


def plot_confusion_matrix(confusion: dict, output_path: Path, threshold: float) -> Path:
    matrix = np.array([[confusion["tn"], confusion["fp"]], [confusion["fn"], confusion["tp"]]])
    fig, ax = plt.subplots(figsize=(5, 5))
    sns.heatmap(matrix, annot=True, fmt="d", cmap="Blues", cbar=False, ax=ax,
                xticklabels=["Pred: No Sepsis", "Pred: Sepsis"],
                yticklabels=["True: No Sepsis", "True: Sepsis"])
    ax.set_title(f"Confusion Matrix (threshold={threshold:.3f})")
    return _save(fig, output_path)


def plot_training_curves(history: dict, output_path: Path) -> Path:
    metrics = [m for m in ("loss", "auroc", "auprc", "precision", "recall") if m in history]
    fig, axes = plt.subplots(1, len(metrics), figsize=(5 * len(metrics), 4))
    if len(metrics) == 1:
        axes = [axes]
    epochs = range(1, len(history[metrics[0]]) + 1)
    for ax, metric in zip(axes, metrics):
        ax.plot(epochs, history[metric], label=f"train_{metric}", color="#4C72B0")
        val_key = f"val_{metric}"
        if val_key in history:
            ax.plot(epochs, history[val_key], label=f"val_{metric}", color="#C44E52")
        ax.set_xlabel("Epoch")
        ax.set_title(metric)
        ax.legend()
    fig.tight_layout()
    return _save(fig, output_path)
