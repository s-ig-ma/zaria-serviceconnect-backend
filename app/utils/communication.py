import logging

from sqlalchemy.exc import SQLAlchemyError

from app.models.models import Complaint, Notification, Provider, User
from app.utils.push_notifications import send_push_to_user

logger = logging.getLogger(__name__)


def create_notification(
    db,
    *,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "general",
    related_id: int | None = None,
):
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        related_id=related_id,
    )

    try:
        with db.begin_nested():
            db.add(notification)
            db.flush()
            send_push_to_user(
                db,
                user_id=user_id,
                title=title,
                message=message,
                data={
                    "type": notification_type,
                    "related_id": related_id,
                    "notification_id": notification.id,
                },
            )
        return notification
    except SQLAlchemyError:
        logger.exception("Notification persistence failed for user_id=%s", user_id)
        return None
    except Exception:
        logger.exception("Notification delivery failed for user_id=%s", user_id)
        return None


def get_complaint_participants(complaint: Complaint) -> tuple[int, int]:
    resident_user_id = complaint.user_id
    provider_user_id = complaint.provider.user_id if complaint.provider else None
    if provider_user_id is None:
        raise ValueError("Complaint provider user could not be resolved.")
    return resident_user_id, provider_user_id


def get_provider_user_id(provider: Provider | None) -> int | None:
    return provider.user_id if provider else None
