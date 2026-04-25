import base64
import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.models import DeviceToken

logger = logging.getLogger(__name__)


def _load_firebase_modules():
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging
        return firebase_admin, credentials, messaging
    except Exception:
        logger.exception("Firebase Admin SDK could not be imported.")
        return None, None, None


def _normalize_private_key(service_account: dict) -> dict:
    private_key = service_account.get("private_key")
    if isinstance(private_key, str):
        service_account["private_key"] = private_key.replace("\\n", "\n")
    return service_account


def _get_service_account_info() -> dict | None:
    if settings.FIREBASE_SERVICE_ACCOUNT_JSON:
        try:
            return _normalize_private_key(json.loads(settings.FIREBASE_SERVICE_ACCOUNT_JSON))
        except json.JSONDecodeError:
            logger.exception("FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON.")
            return None

    if settings.FIREBASE_SERVICE_ACCOUNT_BASE64:
        try:
            decoded = base64.b64decode(settings.FIREBASE_SERVICE_ACCOUNT_BASE64).decode("utf-8")
            return _normalize_private_key(json.loads(decoded))
        except Exception:
            logger.exception("FIREBASE_SERVICE_ACCOUNT_BASE64 could not be decoded as Firebase JSON.")
            return None

    return None


def _get_firebase_app():
    firebase_admin, credentials, _ = _load_firebase_modules()
    if firebase_admin is None or credentials is None:
        return None

    if firebase_admin._apps:
        return firebase_admin.get_app()

    service_account_info = _get_service_account_info()
    if service_account_info:
        firebase_credentials = credentials.Certificate(service_account_info)
        return firebase_admin.initialize_app(firebase_credentials)

    if settings.FIREBASE_SERVICE_ACCOUNT_PATH:
        service_account_path = Path(settings.FIREBASE_SERVICE_ACCOUNT_PATH)
        if not service_account_path.exists():
            logger.error("Firebase service account file does not exist: %s", service_account_path)
            return None

        firebase_credentials = credentials.Certificate(str(service_account_path))
        return firebase_admin.initialize_app(firebase_credentials)

    logger.warning(
        "Firebase push notifications are disabled. Set FIREBASE_SERVICE_ACCOUNT_JSON, "
        "FIREBASE_SERVICE_ACCOUNT_BASE64, or FIREBASE_SERVICE_ACCOUNT_PATH."
    )
    return None


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
        logger.warning("Skipping push notification for user_id=%s because Firebase is not configured.", user_id)
        return

    active_tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == user_id, DeviceToken.is_active.is_(True))
        .all()
    )
    if not active_tokens:
        logger.info("No active device tokens found for user_id=%s.", user_id)
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
                logger.info("Removed invalid Firebase token for user_id=%s.", user_id)
            else:
                logger.exception("Failed to send Firebase push notification to user_id=%s.", user_id)
