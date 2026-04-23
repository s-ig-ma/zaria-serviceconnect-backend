from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import DeviceToken, Notification, User
from app.schemas.communication_schemas import DeviceTokenRegister, DeviceTokenRemove, NotificationOut
from app.schemas.schemas import MessageResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/my", response_model=List[NotificationOut])
def get_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )


@router.patch("/{notification_id}/read", response_model=NotificationOut)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.patch("/read-all", response_model=MessageResponse)
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifications = db.query(Notification).filter(Notification.user_id == current_user.id).all()
    for notification in notifications:
        notification.is_read = True
    db.commit()
    return {"message": "All notifications marked as read.", "success": True}


@router.post("/devices/register", response_model=MessageResponse)
def register_device_token(
    payload: DeviceTokenRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token_value = payload.token.strip()
    device_token = db.query(DeviceToken).filter(DeviceToken.token == token_value).first()

    if not device_token:
        device_token = DeviceToken(
            user_id=current_user.id,
            token=token_value,
            platform="android",
            device_name=(payload.device_name or "").strip() or None,
            is_active=True,
        )
        db.add(device_token)
    else:
        device_token.user_id = current_user.id
        device_token.platform = "android"
        device_token.device_name = (payload.device_name or "").strip() or None
        device_token.is_active = True
        device_token.last_seen_at = func.now()

    db.commit()
    return {"message": "Device token registered successfully.", "success": True}


@router.post("/devices/unregister", response_model=MessageResponse)
def unregister_device_token(
    payload: DeviceTokenRemove,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_token = (
        db.query(DeviceToken)
        .filter(DeviceToken.token == payload.token.strip(), DeviceToken.user_id == current_user.id)
        .first()
    )
    if device_token:
        db.delete(device_token)
        db.commit()
        return {"message": "Device token removed successfully.", "success": True}

    return {"message": "Device token was already removed.", "success": True}
