import logging
import smtplib
from email.message import EmailMessage
from typing import Mapping

from app.core.config import settings

logger = logging.getLogger(__name__)


def _is_email_configured() -> bool:
    return bool(
        settings.ADMIN_ACTIVITY_EMAIL
        and settings.SMTP_HOST
        and settings.SMTP_PORT
        and settings.SMTP_USERNAME
        and settings.SMTP_PASSWORD
        and settings.SMTP_FROM_EMAIL
    )


def _format_activity_body(activity: str, details: Mapping[str, object | None]) -> str:
    lines = [
        "A new activity occurred in Need Service Connect.",
        "",
        f"Activity: {activity}",
        "",
        "Details:",
    ]
    for key, value in details.items():
        if value is not None and value != "":
            label = key.replace("_", " ").title()
            lines.append(f"- {label}: {value}")
    return "\n".join(lines)


def send_admin_activity_email(
    *,
    activity: str,
    details: Mapping[str, object | None],
):
    if not _is_email_configured():
        logger.warning(
            "Admin activity email skipped because SMTP_PASSWORD or other email settings are missing."
        )
        return

    message = EmailMessage()
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = settings.ADMIN_ACTIVITY_EMAIL
    message["Subject"] = f"Need Service Connect Activity: {activity}"
    message.set_content(_format_activity_body(activity, details))

    try:
        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=settings.SMTP_TIMEOUT_SECONDS,
        ) as smtp:
            if settings.SMTP_USE_TLS:
                smtp.starttls()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)
    except Exception:
        logger.exception("Failed to send admin activity email for %s", activity)
