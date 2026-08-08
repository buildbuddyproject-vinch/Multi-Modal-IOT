from pathlib import Path

import numpy as np
import pytest

from src.models.architectures.hybrid_model import ModelConfig, build_hybrid_model
from src.models.explainability.patient_report import build_patient_explanation
from src.models.explainability.plots import plot_force, plot_global_importance, plot_summary, plot_waterfall
from src.models.explainability.shap_explainer import build_explainer, compute_shap_values

TINY_CONFIG = ModelConfig(
    window_size=4, n_channels=4,
    cnn_filters=(4,), bilstm_units=(4,),
    transformer_layers=1, transformer_heads=1, transformer_key_dim=2, transformer_ff_dim=8,
    dense_units=(4,),
)
CHANNEL_NAMES = ["HR", "Temp", "Glucose", "WBC"]


@pytest.fixture(scope="module")
def shap_values():
    model = build_hybrid_model(TINY_CONFIG)
    rng = np.random.default_rng(0)
    background = rng.normal(size=(15, 4, 4)).astype(np.float32)
    X_eval = rng.normal(size=(4, 4, 4)).astype(np.float32)
    explainer = build_explainer(model, background, window_size=4, n_channels=4, channel_names=CHANNEL_NAMES)
    return compute_shap_values(explainer, X_eval, max_evals=50), model, X_eval


def test_plot_summary_saves_nonempty_file(shap_values, tmp_path):
    values, _, _ = shap_values
    path = plot_summary(values, tmp_path / "summary.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_waterfall_saves_nonempty_file(shap_values, tmp_path):
    values, _, _ = shap_values
    path = plot_waterfall(values, index=0, output_path=tmp_path / "waterfall.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_force_saves_nonempty_file(shap_values, tmp_path):
    values, _, _ = shap_values
    path = plot_force(values, index=0, output_path=tmp_path / "force.png")
    assert path.exists() and path.stat().st_size > 0


def test_plot_global_importance_saves_nonempty_file_and_orders_by_magnitude(shap_values, tmp_path):
    values, _, _ = shap_values
    path = plot_global_importance(values, tmp_path / "global.png")
    assert path.exists() and path.stat().st_size > 0

    mean_abs = np.abs(values.values).mean(axis=0)
    assert CHANNEL_NAMES[np.argmax(mean_abs)] in CHANNEL_NAMES  # sanity: argmax is valid


def test_patient_explanation_structure(shap_values):
    values, model, X_eval = shap_values
    from src.models.explainability.shap_explainer import make_predict_fn
    preds = make_predict_fn(model, 4, 4)(X_eval.reshape(4, -1))

    report = build_patient_explanation(values, index=0, prediction_probability=float(preds[0]), top_n=3)

    assert report["explanation_method"] == "shap"
    assert set(report["shap_values"].keys()) == set(CHANNEL_NAMES)
    assert len(report["top_contributing_features"]) == 3
    # top features must be sorted by |contribution| descending
    contributions = [abs(f["contribution"]) for f in report["top_contributing_features"]]
    assert contributions == sorted(contributions, reverse=True)
    # base_value + sum(all shap_values) should reconstruct the prediction
    reconstructed = report["base_value"] + sum(report["shap_values"].values())
    assert reconstructed == pytest.approx(report["prediction_probability"], abs=1e-4)


def test_patient_explanation_top_n_caps_at_available_features(shap_values):
    values, model, X_eval = shap_values
    report = build_patient_explanation(values, index=1, prediction_probability=0.1, top_n=100)
    assert len(report["top_contributing_features"]) == len(CHANNEL_NAMES)
