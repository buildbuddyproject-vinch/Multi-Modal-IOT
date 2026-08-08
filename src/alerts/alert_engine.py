"""Decides whether a new prediction should raise a clinician-facing alert, and
if so, dispatches it over every configured channel and records both the alert
and an audit trail entry. Wired into POST /predictions (src/api/routes/predictions.py)
so every prediction -- real model inference now, Phase 2 IoT-triggered inference
later -- goes through the same path; nothing about this module cares where the
prediction came from.
"""
import logging
from datetime import datetime, timezone

from src.alerts.dispatchers.email_dispatcher import send_email_alert
from src.alerts.dispatchers.mqtt_dispatcher import publish_alert_mqtt
from src.alerts.dispatchers.telegram_dispatcher import send_telegram_alert
from src.alerts.reason import summarize_abnormal_vitals
from src.config.settings import get_settings
from src.database.mongodb.repositories import AlertRepository, AuditLogRepository, VitalsRepository

logger = logging.getLogger(__name__)

RISK_RANK = {"Low": 0, "Medium": 1, "High": 2, "Critical": 3}


class AlertEngine:
    def __init__(self, alert_repo: AlertRepository, audit_repo: AuditLogRepository, vitals_repo: VitalsRepository):
        self.alert_repo = alert_repo
        self.audit_repo = audit_repo
        self.vitals_repo = vitals_repo

    def evaluate_and_dispatch(self, patient_id: str, prediction: dict) -> str | None:
        """Returns the new alert's id, or None if no alert was raised (risk too
        low, or suppressed by cooldown)."""
        settings = get_settings()
        risk_level = prediction["risk_level"]
        if risk_level not in settings.alert_trigger_risk_levels_list:
            return None

        if self._suppressed_by_cooldown(patient_id, risk_level, settings.alert_cooldown_minutes):
            logger.info("Suppressing %s alert for %s: within cooldown, no risk escalation", risk_level, patient_id)
            return None

        latest_vitals = self.vitals_repo.get_latest(patient_id)
        reason = summarize_abnormal_vitals((latest_vitals or {}).get("channels"))
        why_clause = f" -- {reason}" if reason else " -- driven by a multi-channel pattern (see SHAP explanation)"
        message = (
            f"[{risk_level}] Sepsis risk for patient {patient_id}: "
            f"{prediction['sepsis_probability']:.0%} probability{why_clause}"
        )
        dispatch_status = {
            "telegram": send_telegram_alert(message),
            "email": send_email_alert(f"Sepsis Alert ({risk_level}) - Patient {patient_id}", message),
            "mqtt": publish_alert_mqtt(patient_id, risk_level, message),
        }
        channels_dispatched = [channel for channel, status in dispatch_status.items() if status != "skipped"]

        prediction_id = prediction.get("id") or (str(prediction["_id"]) if "_id" in prediction else None)
        alert_id = self.alert_repo.create(
            patient_id, risk_level, message,
            prediction_id=prediction_id,
            channels_dispatched=channels_dispatched,
            dispatch_status=dispatch_status,
        )
        self.audit_repo.log(
            actor="system", action="alert_dispatched", target_type="alert", target_id=alert_id,
            details={"patient_id": patient_id, "risk_level": risk_level, "dispatch_status": dispatch_status},
        )
        logger.warning("Alert %s dispatched for patient %s (risk=%s, channels=%s)", alert_id, patient_id, risk_level, channels_dispatched)
        return alert_id

    def _suppressed_by_cooldown(self, patient_id: str, risk_level: str, cooldown_minutes: int) -> bool:
        recent = self.alert_repo.list_alerts(patient_id=patient_id, limit=1)
        if not recent:
            return False
        last_alert = recent[0]
        escalated = RISK_RANK[risk_level] > RISK_RANK.get(last_alert["risk_level"], 0)
        if escalated:
            return False
        age_minutes = (datetime.now(timezone.utc) - last_alert["created_at"]).total_seconds() / 60.0
        return age_minutes < cooldown_minutes
