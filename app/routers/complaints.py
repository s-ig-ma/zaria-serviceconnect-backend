from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.models import (
    Booking,
    Complaint,
    ComplaintAction,
    ComplaintActionType,
    ComplaintStatus,
    Provider,
    ProviderStatus,
    User,
    UserRole,
)
from app.schemas.communication_schemas import (
    ComplaintActionCreate,
    ComplaintActionOut,
)
from app.schemas.complaint_schemas import ComplaintCreate, ComplaintOut, ComplaintResolve
from app.utils.communication import create_notification, get_complaint_participants

router = APIRouter(prefix="/complaints", tags=["Complaints"])


def _get_complaint_or_404(complaint_id: int, db: Session) -> Complaint:
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")
    return complaint


def _ensure_complaint_access(complaint: Complaint, current_user: User):
    provider_user_id = complaint.provider.user_id if complaint.provider else None
    allowed_ids = {complaint.user_id, provider_user_id}
    if current_user.role.value != "admin" and current_user.id not in allowed_ids:
        raise HTTPException(status_code=403, detail="Access denied.")


@router.post("/", response_model=ComplaintOut, status_code=201)
def submit_complaint(
    data: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can submit complaints.")

    booking = (
        db.query(Booking)
        .filter(Booking.id == data.booking_id, Booking.resident_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found. You can only complain about your own bookings.",
        )

    existing = db.query(Complaint).filter(Complaint.booking_id == data.booking_id).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A complaint has already been submitted for this booking.",
        )

    complaint = Complaint(
        booking_id=data.booking_id,
        user_id=current_user.id,
        provider_id=booking.provider_id,
        message=data.message,
        status=ComplaintStatus.open,
    )
    db.add(complaint)
    db.flush()

    provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()
    provider_user_id = provider.user_id if provider else None
    if provider_user_id is None:
        raise HTTPException(status_code=404, detail="Complaint provider could not be resolved.")
    admin_users = db.query(User).filter(User.role == UserRole.admin, User.is_active.is_(True)).all()
    for admin in admin_users:
        create_notification(
            db,
            user_id=admin.id,
            title="New complaint submitted",
            message=f"{current_user.name} submitted complaint #{complaint.id}.",
            notification_type="complaint",
            related_id=complaint.id,
        )
    create_notification(
        db,
        user_id=provider_user_id,
        title="Complaint submitted",
        message="A resident submitted a complaint related to one of your bookings.",
        notification_type="complaint",
        related_id=complaint.id,
    )

    db.commit()
    db.refresh(complaint)
    return complaint


@router.get("/my", response_model=List[ComplaintOut])
def get_my_complaints(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value == "resident":
        query = db.query(Complaint).filter(Complaint.user_id == current_user.id)
    elif current_user.role.value == "provider":
        provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider profile not found.")
        query = db.query(Complaint).filter(Complaint.provider_id == provider.id)
    else:
        raise HTTPException(status_code=403, detail="Only residents and providers can access this.")

    return query.order_by(Complaint.created_at.desc()).all()


@router.get("/", response_model=List[ComplaintOut])
def get_all_complaints(
    status: Optional[str] = Query(None, description="Filter by status: open, in_review, resolved"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    query = db.query(Complaint)
    if status:
        valid_statuses = ["open", "in_review", "resolved"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid_statuses}")
        query = query.filter(Complaint.status == status)
    return query.order_by(Complaint.created_at.desc()).all()


@router.put("/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    complaint_id: int,
    data: ComplaintResolve,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    complaint = _get_complaint_or_404(complaint_id, db)

    valid_statuses = ["open", "in_review", "resolved"]
    if data.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid_statuses}")

    complaint.status = data.status
    if data.resolution_note:
        complaint.resolution_note = data.resolution_note

    resident_user_id, provider_user_id = get_complaint_participants(complaint)
    for user_id in {resident_user_id, provider_user_id}:
        create_notification(
            db,
            user_id=user_id,
            title="Complaint status updated",
            message=f"Complaint #{complaint.id} is now {data.status}.",
            notification_type="complaint",
            related_id=complaint.id,
        )

    db.commit()
    db.refresh(complaint)
    return complaint


@router.post("/{complaint_id}/actions", response_model=ComplaintActionOut, status_code=201)
def create_complaint_action(
    complaint_id: int,
    data: ComplaintActionCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    complaint = _get_complaint_or_404(complaint_id, db)

    valid_action_types = [action.value for action in ComplaintActionType]
    if data.action_type not in valid_action_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type. Choose from: {valid_action_types}",
        )

    target_user = None
    if data.target_user_id is not None:
        target_user = db.query(User).filter(User.id == data.target_user_id).first()
        if not target_user:
            raise HTTPException(status_code=404, detail="Target user not found.")

    action_type = ComplaintActionType(data.action_type)

    if action_type == ComplaintActionType.provider_suspension:
        provider = db.query(Provider).filter(Provider.id == complaint.provider_id).first()
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found.")
        provider.status = ProviderStatus.suspended
        target_user = provider.user
    elif action_type == ComplaintActionType.account_deactivation:
        if not target_user:
            raise HTTPException(status_code=400, detail="Select the user account to deactivate.")
        target_user.is_active = False

    action = ComplaintAction(
        complaint_id=complaint.id,
        admin_user_id=admin.id,
        target_user_id=target_user.id if target_user else None,
        action_type=action_type,
        note=data.note,
    )
    db.add(action)
    db.flush()

    if target_user:
        create_notification(
            db,
            user_id=target_user.id,
            title="Admin action recorded",
            message=data.note or f"An admin recorded a {data.action_type} action on your account.",
            notification_type="complaint_action",
            related_id=complaint.id,
        )

    db.commit()
    db.refresh(action)
    return action


@router.get("/{complaint_id}/actions", response_model=List[ComplaintActionOut])
def get_complaint_actions(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = _get_complaint_or_404(complaint_id, db)
    _ensure_complaint_access(complaint, current_user)

    return (
        db.query(ComplaintAction)
        .filter(ComplaintAction.complaint_id == complaint_id)
        .order_by(ComplaintAction.created_at.desc())
        .all()
    )


@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = _get_complaint_or_404(complaint_id, db)
    _ensure_complaint_access(complaint, current_user)
    return complaint
