"""SHAP plot generation: summary, waterfall, force, and a global (mean |SHAP|)
importance bar chart, all saved as PNG files."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shap


def _save_current_figure(output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    return output_path


def plot_summary(shap_values: shap.Explanation, output_path: Path, max_display: int = 20) -> Path:
    shap.summary_plot(shap_values, show=False, max_display=max_display)
    return _save_current_figure(output_path)


def plot_waterfall(shap_values: shap.Explanation, index: int, output_path: Path, max_display: int = 15) -> Path:
    shap.plots.waterfall(shap_values[index], show=False, max_display=max_display)
    return _save_current_figure(output_path)


def plot_force(shap_values: shap.Explanation, index: int, output_path: Path) -> Path:
    shap.plots.force(
        shap_values.base_values[index], shap_values.values[index], shap_values.data[index],
        feature_names=shap_values.feature_names, matplotlib=True, show=False,
    )
    return _save_current_figure(output_path)


def plot_global_importance(shap_values: shap.Explanation, output_path: Path, max_display: int = 20) -> Path:
    """Mean |SHAP value| per channel across all explained instances -- the
    'global explanation' view: which channels matter most for the model overall,
    not just for one patient."""
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    order = np.argsort(mean_abs)[::-1][:max_display]
    names = np.array(shap_values.feature_names)[order]
    values = mean_abs[order]

    fig, ax = plt.subplots(figsize=(8, max(4, 0.35 * len(names))))
    ax.barh(range(len(names)), values[::-1], color="#4C72B0")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names[::-1])
    ax.set_xlabel("Mean |SHAP value|")
    ax.set_title(f"Global Feature Importance (SHAP, n={shap_values.values.shape[0]} windows)")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return Path(output_path)
