"""Step 6 CLI entry point: SHAP explainability for the trained hybrid model.

Produces:
- A global summary plot + mean|SHAP| importance bar chart over a sample of test windows.
- Waterfall + force plots for a handful of representative patients (highest-confidence
  true positive, a false negative, and a confident true negative).
- A per-patient JSON explanation report for each of those, shaped to match the
  `prediction_history` MongoDB schema (see docs/architecture/database_design.md).

Usage: python scripts/run_shap_explainability.py [--n-background 50] [--n-global 200] [--max-evals 150]
"""
import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import keras
import numpy as np

# Ensure custom Keras classes (SinusoidalPositionalEncoding, BinaryFocalLoss) are
# registered before load_model() tries to deserialize a model that uses them.
import src.models.architectures.transformer_block  # noqa: F401
import src.models.training.losses  # noqa: F401

from src.config.settings import get_settings
from src.data.schema import CLINICAL_CHANNELS
from src.models.explainability.patient_report import build_patient_explanation
from src.models.explainability.plots import plot_force, plot_global_importance, plot_summary, plot_waterfall
from src.models.explainability.shap_explainer import build_explainer, compute_shap_values, make_predict_fn

logger = logging.getLogger(__name__)


def select_example_windows(y: np.ndarray, y_prob: np.ndarray) -> dict[str, int]:
    """Picks one illustrative window per case: the most confident correct sepsis
    call, the most confident miss (false negative), and a confident correct
    no-sepsis call -- covering the cases a clinician would actually want explained."""
    positive_idx = np.where(y == 1)[0]
    negative_idx = np.where(y == 0)[0]

    selections = {}
    if len(positive_idx) > 0:
        selections["true_positive_high_confidence"] = int(positive_idx[np.argmax(y_prob[positive_idx])])
        selections["false_negative_high_confidence_miss"] = int(positive_idx[np.argmin(y_prob[positive_idx])])
    if len(negative_idx) > 0:
        selections["true_negative_high_confidence"] = int(negative_idx[np.argmin(y_prob[negative_idx])])
    return selections


def main():
    parser = argparse.ArgumentParser(description="Run Step 6 SHAP explainability")
    parser.add_argument("--n-background", type=int, default=50)
    parser.add_argument("--n-global", type=int, default=200)
    parser.add_argument("--max-evals", type=int, default=150)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    settings = get_settings()
    processed_dir = settings.processed_dir / "physionet2019"
    model_path = settings.resolve_path("./models") / "saved" / "final_model.keras"
    output_dir = settings.resolve_path("./models") / "explainability"
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Loading model from %s", model_path)
    model = keras.models.load_model(model_path, compile=False)
    window_size, n_channels = model.input_shape[1], model.input_shape[2]

    with np.load(processed_dir / "train.npz") as data:
        X_train = data["X"]
    with np.load(processed_dir / "test.npz") as data:
        X_test, y_test = data["X"], data["y"]

    rng = np.random.default_rng(42)
    background = X_train[rng.choice(len(X_train), args.n_background, replace=False)]

    logger.info("Scoring test set to select representative windows")
    predict_fn = make_predict_fn(model, window_size, n_channels)
    y_prob_test = predict_fn(X_test.reshape(len(X_test), -1))

    explainer = build_explainer(model, background, window_size, n_channels, channel_names=CLINICAL_CHANNELS)

    # --- Global explanation ---
    global_idx = rng.choice(len(X_test), min(args.n_global, len(X_test)), replace=False)
    logger.info("Computing global SHAP values on %d windows (max_evals=%d)", len(global_idx), args.max_evals)
    global_shap = compute_shap_values(explainer, X_test[global_idx], max_evals=args.max_evals)

    plot_summary(global_shap, output_dir / "shap_summary_plot.png")
    plot_global_importance(global_shap, output_dir / "shap_global_importance.png")
    logger.info("Saved global summary/importance plots")

    # --- Patient-level explanations ---
    selections = select_example_windows(y_test, y_prob_test)
    patient_indices = list(selections.values())
    logger.info("Computing patient-level SHAP values for %d example windows: %s", len(patient_indices), selections)
    patient_shap = compute_shap_values(explainer, X_test[patient_indices], max_evals=args.max_evals)

    reports = {}
    for local_i, (case_name, test_idx) in enumerate(selections.items()):
        plot_waterfall(patient_shap, index=local_i, output_path=output_dir / f"waterfall_{case_name}.png")
        plot_force(patient_shap, index=local_i, output_path=output_dir / f"force_{case_name}.png")
        report = build_patient_explanation(
            patient_shap, index=local_i,
            prediction_probability=float(y_prob_test[test_idx]),
        )
        report["case"] = case_name
        report["true_label"] = int(y_test[test_idx])
        reports[case_name] = report
        logger.info("Case '%s': true_label=%d, predicted_probability=%.4f, top feature=%s",
                    case_name, report["true_label"], report["prediction_probability"],
                    report["top_contributing_features"][0]["feature"])

    (output_dir / "patient_explanations.json").write_text(json.dumps(reports, indent=2))
    logger.info("Saved patient explanations -> %s", output_dir / "patient_explanations.json")

    print(f"\nStep 6 SHAP explainability artifacts saved under {output_dir}")


if __name__ == "__main__":
    main()
