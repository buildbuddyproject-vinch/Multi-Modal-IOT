"""Sends an alert email over SMTP using the stdlib only (smtplib/email) -- a
single templated message per alert doesn't need an extra dependency."""
import logging
import smtplib
from email.mime.text import MIMEText

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


def send_email_alert(subject: str, body: str) -> str:
    """Returns 'sent', 'failed', or 'skipped' (not configured) -- never raises,
    so a notification-channel outage can't take down alert creation itself."""
    settings = get_settings()
    if not settings.smtp_host or not settings.alert_email_to:
        return "skipped"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.alert_email_from or settings.smtp_username
    msg["To"] = settings.alert_email_to

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10.0) as server:
            server.starttls()
            if settings.smtp_username:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
        return "sent"
    except (smtplib.SMTPException, OSError):
        logger.exception("Email alert dispatch failed")
        return "failed"
