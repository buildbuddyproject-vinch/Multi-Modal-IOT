"""Maps a model sepsis_probability to the predicted_label / risk_level fields
stored on `predictions` documents (docs/architecture/database_design.md).

`predicted_label` uses the best-F1 operating threshold chosen during evaluation
(Step 5, models/evaluation/metrics.json) rather than a naive 0.5 cutoff -- with a
~1.9% positive rate, 0.5 predicts "no sepsis" for every patient. `risk_level`
buckets the raw probability more granularly for the dashboard/alerting UI, using
that same threshold as the Medium/High boundary so "High" always implies the
model would flag the case."""
import json

from src.config.settings import PROJECT_ROOT

_FALLBACK_THRESHOLD = 0.20656414330005646  # metrics.json's metrics_at_best_f1_threshold, at time of Step 5 training


def _resolve_threshold() -> float:
    metrics_path = PROJECT_ROOT / "models" / "evaluation" / "metrics.json"
    if not metrics_path.exists():
        return _FALLBACK_THRESHOLD
    try:
        with open(metrics_path) as f:
            return json.load(f)["metrics_at_best_f1_threshold"]["threshold"]
    except (KeyError, json.JSONDecodeError):
        return _FALLBACK_THRESHOLD


BEST_F1_THRESHOLD = _resolve_threshold()


def predicted_label(sepsis_probability: float) -> int:
    return int(sepsis_probability >= BEST_F1_THRESHOLD)


def probability_to_risk_level(sepsis_probability: float) -> str:
    if sepsis_probability >= 0.5:
        return "Critical"
    if sepsis_probability >= BEST_F1_THRESHOLD:
        return "High"
    if sepsis_probability >= 0.10:
        return "Medium"
    return "Low"
