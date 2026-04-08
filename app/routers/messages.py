from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import Complaint, Message, User
from app.schemas.communication_schemas import MessageCreate, MessageOut
from app.utils.communication import create_notification

router = APIRouter(prefix="/messages", tags=["Messages"])


def _get_message(message_id: int, db: Session) -> Message:
    message = db.query(Message).filter(Message.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    return message


def _ensure_complaint_access(complaint: Complaint, current_user: User):
    participant_ids = {
        complaint.user_id,
        complaint.provider.user_id if complaint.provider else None,
    }
    if current_user.role.value != "admin" and current_user.id not in participant_ids:
        raise HTTPException(status_code=403, detail="Access denied.")


def _get_complaint_user_ids(complaint: Complaint) -> tuple[int, Optional[int]]:
    return complaint.user_id, complaint.provider.user_id if complaint.provider else None


def _get_admin_ids(db: Session) -> List[int]:
    return [
        user.id
        for user in db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    ]


def _get_default_admin(db: Session) -> User:
    admin = (
        db.query(User)
        .filter(User.role == "admin", User.is_active.is_(True))
        .order_by(User.id.asc())
        .first()
    )
    if not admin:
        raise HTTPException(status_code=404, detail="No active admin account is available.")
    return admin


def _validate_complaint_message_pair(
    complaint: Complaint,
    current_user: User,
    recipient: User,
):
    resident_user_id, provider_user_id = _get_complaint_user_ids(complaint)

    if current_user.role.value == "admin":
        if recipient.id not in {resident_user_id, provider_user_id}:
            raise HTTPException(
                status_code=403,
                detail="Admin can only message the complaint resident or provider.",
            )
        return

    if current_user.id == resident_user_id:
        if recipient.role.value != "admin":
            raise HTTPException(
                status_code=403,
                detail="Residents can only send complaint messages to admin.",
            )
        return

    if current_user.id == provider_user_id:
        if recipient.role.value != "admin":
            raise HTTPException(
                status_code=403,
                detail="Providers can only send complaint messages to admin.",
            )
        return

    raise HTTPException(status_code=403, detail="This complaint message is not allowed.")


@router.get("/", response_model=List[MessageOut])
def get_my_messages(
    complaint_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Message).filter(
        or_(
            Message.sender_user_id == current_user.id,
            Message.recipient_user_id == current_user.id,
        )
    )

    if complaint_id is not None:
        complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        _ensure_complaint_access(complaint, current_user)
        query = query.filter(Message.complaint_id == complaint_id)

    return query.order_by(Message.created_at.asc()).all()


@router.get("/complaint/{complaint_id}", response_model=List[MessageOut])
def get_complaint_messages(
    complaint_id: int,
    counterpart_user_id: Optional[int] = Query(
        None,
        description="For admin: filter complaint messages to a resident/admin or provider/admin thread.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    _ensure_complaint_access(complaint, current_user)

    query = db.query(Message).filter(Message.complaint_id == complaint_id)
    resident_user_id, provider_user_id = _get_complaint_user_ids(complaint)
    admin_ids = _get_admin_ids(db)

    if current_user.role.value == "admin":
        if counterpart_user_id is not None:
            if counterpart_user_id not in {resident_user_id, provider_user_id}:
                raise HTTPException(status_code=403, detail="Invalid complaint conversation target.")
            query = query.filter(
                or_(
                    and_(
                        Message.sender_user_id.in_(admin_ids),
                        Message.recipient_user_id == counterpart_user_id,
                    ),
                    and_(
                        Message.sender_user_id == counterpart_user_id,
                        Message.recipient_user_id.in_(admin_ids),
                    ),
                )
            )
    else:
        query = query.filter(
            or_(
                and_(
                    Message.sender_user_id == current_user.id,
                    Message.recipient_user_id.in_(admin_ids),
                ),
                and_(
                    Message.sender_user_id.in_(admin_ids),
                    Message.recipient_user_id == current_user.id,
                ),
            )
        )

    return query.order_by(Message.created_at.asc()).all()


@router.post("/", response_model=MessageOut, status_code=201)
def send_message(
    data: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipient = None
    if data.recipient_user_id is not None:
        recipient = db.query(User).filter(User.id == data.recipient_user_id).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found.")
        if recipient.id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot send a message to yourself.")

    complaint = None
    if data.complaint_id is not None:
        complaint = db.query(Complaint).filter(Complaint.id == data.complaint_id).first()
        if not complaint:
            raise HTTPException(status_code=404, detail="Complaint not found.")
        _ensure_complaint_access(complaint, current_user)
        if recipient is None:
            if current_user.role.value == "admin":
                raise HTTPException(
                    status_code=400,
                    detail="Admin must choose whether to message the resident or provider.",
                )
            recipient = _get_default_admin(db)
        _validate_complaint_message_pair(complaint, current_user, recipient)
    elif current_user.role.value != "admin":
        raise HTTPException(
            status_code=400,
            detail="Resident and provider messages must be linked to a complaint.",
        )
    elif recipient is None:
        raise HTTPException(status_code=400, detail="Recipient is required.")

    cleaned_content = data.content.strip()
    if not cleaned_content:
        raise HTTPException(status_code=400, detail="Message content cannot be empty.")

    message = Message(
        complaint_id=data.complaint_id,
        sender_user_id=current_user.id,
        recipient_user_id=recipient.id,
        content=cleaned_content,
    )
    db.add(message)
    db.flush()

    create_notification(
        db,
        user_id=recipient.id,
        title="New message from admin" if current_user.role.value == "admin" else "New complaint message",
        message=message.content,
        notification_type="message",
        related_id=message.id,
    )

    db.commit()
    db.refresh(message)
    return message


@router.patch("/{message_id}/read", response_model=MessageOut)
def mark_message_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    message = _get_message(message_id, db)
    if current_user.id not in {message.sender_user_id, message.recipient_user_id} and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Access denied.")

    if current_user.id == message.recipient_user_id:
        message.is_read = True
        db.commit()
        db.refresh(message)
    return message
