"""Builds the short, human-readable "why" clause an alert message includes.

Deliberately independent of the deep-learning model's SHAP explanation
(src/models/explainability) -- SHAP is expensive to compute and, for the live
MQTT path (src/services/realtime_pipeline.py), is never computed at all. This
instead runs the same fast, threshold-based checks a bedside monitor would
(broadly qSOFA/SIRS-aligned: temperature, heart rate, respiratory rate, blood
pressure), so an alert always ships with *some* concrete reason, even before
a clinician opens the patient's full SHAP breakdown."""
from typing import Optional

# (low_threshold, high_threshold, unit, human label) -- a reading outside
# [low, high] is called out by name. None means "no bound on that side".
_VITAL_RANGES: dict[str, tuple[Optional[float], Optional[float], str, str]] = {
    "HR": (60.0, 100.0, "bpm", "Heart rate"),
    "O2Sat": (92.0, None, "%", "Oxygen saturation"),
    "Temp": (36.0, 38.3, "°C", "Temperature"),
    "SBP": (90.0, None, "mmHg", "Systolic BP"),
    "MAP": (65.0, None, "mmHg", "MAP"),
    "Resp": (None, 22.0, "breaths/min", "Respiratory rate"),
}


def summarize_abnormal_vitals(channels: Optional[dict], max_findings: int = 3) -> str:
    """Returns a clause like "Fever (38.9°C), Tachycardia (118 bpm)", or ""
    if `channels` is missing/empty or nothing crosses a threshold."""
    if not channels:
        return ""

    findings = []
    for channel, (low, high, unit, label) in _VITAL_RANGES.items():
        value = channels.get(channel)
        if value is None:
            continue
        if low is not None and value < low:
            findings.append(f"Low {label} ({value:.0f}{unit})")
        elif high is not None and value > high:
            findings.append(f"Elevated {label} ({value:.0f}{unit})")

    return ", ".join(findings[:max_findings])
