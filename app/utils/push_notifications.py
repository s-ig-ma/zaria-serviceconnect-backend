from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import DeviceToken


def _load_firebase_modules():
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        return firebase_admin, credentials, messaging
    except Exception:
        return None, None, None


def _get_firebase_app():
    firebase_admin, credentials, _ = _load_firebase_modules()
    if firebase_admin is None:
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    if not settings.FIREBASE_SERVICE_ACCOUNT_PATH:
        return None

    service_account_path = Path(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
    if not service_account_path.exists():
        return None

    firebase_credentials = credentials.Certificate(str(service_account_path))
    return firebase_admin.initialize_app(firebase_credentials)


def deactivate_device_token(db: Session, token_value: str):
    device_token = db.query(DeviceToken).filter(DeviceToken.token == token_value).first()
    if device_token:
        db.delete(device_token)
        db.flush()


def send_push_to_user(
    db: Session,
    *,
    user_id: int,
    title: str,
    message: str,
    data: dict[str, str] | None = None,
):
    _, _, messaging = _load_firebase_modules()
    firebase_app = _get_firebase_app()
    if firebase_app is None or messaging is None:
        return

    active_tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True))
        .all()
    )
    if not active_tokens:
        return

    payload = {key: str(value) for key, value in (data or {}).items() if value is not None}

    for device_token in active_tokens:
        try:
            messaging.send(
                messaging.Message(
                    token=device_token.token,
                    notification=messaging.Notification(title=title, body=message),
                    data=payload,
                    android=messaging.AndroidConfig(priority="high"),
                ),
                app=firebase_app,
            )
        except Exception as exc:
            error_text = str(exc).lower()
            if "registration-token-not-registered" in error_text or "invalid-registration-token" in error_text:
                deactivate_device_token(db, device_token.token)
