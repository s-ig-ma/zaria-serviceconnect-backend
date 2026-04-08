from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.models import Booking, BookingStatus, Provider, User
from app.schemas.schemas import BookingCreate, BookingDetailOut, BookingStatusUpdate, MessageResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])

BUSY_BOOKING_CAP = 2
OPEN_BOOKING_STATUSES = [
    BookingStatus.pending,
    BookingStatus.accepted,
    BookingStatus.completion_requested,
]


def count_open_bookings(db: Session, provider_id: int, exclude_booking_id: int | None = None) -> int:
    query = db.query(Booking).filter(
        Booking.provider_id == provider_id,
        Booking.status.in_(OPEN_BOOKING_STATUSES),
    )
    if exclude_booking_id is not None:
        query = query.filter(Booking.id != exclude_booking_id)
    return query.count()


@router.post("/", response_model=BookingDetailOut, status_code=201)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can create bookings.")

    provider = db.query(Provider).filter(Provider.id == data.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if provider.status.value != "approved":
        raise HTTPException(status_code=400, detail="Provider is not approved.")
    if provider.availability_status == "offline":
        raise HTTPException(status_code=400, detail="This provider is currently offline and cannot be booked.")

    open_bookings = count_open_bookings(db, provider.id)
    if provider.availability_status == "busy" and open_bookings >= BUSY_BOOKING_CAP:
        raise HTTPException(
            status_code=400,
            detail=f"This provider is busy and has reached the current booking limit of {BUSY_BOOKING_CAP}.",
        )

    service_address = (data.service_address or current_user.home_address or "").strip()
    if not service_address:
        raise HTTPException(
            status_code=400,
            detail="Please enter the home address for this booking.",
        )

    booking = Booking(
        resident_id=current_user.id,
        provider_id=data.provider_id,
        service_description=data.service_description,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        service_address=service_address,
        notes=data.notes,
        status=BookingStatus.pending,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my/resident", response_model=List[BookingDetailOut])
def get_resident_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can access this.")

    return (
        db.query(Booking)
        .filter(Booking.resident_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.get("/my/provider", response_model=List[BookingDetailOut])
def get_provider_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "provider":
        raise HTTPException(status_code=403, detail="Only providers can access this.")

    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")

    return (
        db.query(Booking)
        .filter(Booking.provider_id == provider.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.get("/admin/all", response_model=List[BookingDetailOut])
def admin_get_all_bookings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return db.query(Booking).order_by(Booking.created_at.desc()).all()


@router.patch("/{booking_id}/status", response_model=BookingDetailOut)
def update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    requested_status = data.status
    valid_statuses = ["accepted", "completion_requested", "completed", "cancelled", "declined"]
    if requested_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {valid_statuses}",
        )

    provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()

    if requested_status in ["accepted", "declined", "completion_requested"]:
        provider_for_user = db.query(Provider).filter(Provider.user_id == current_user.id).first()
        if not provider_for_user or booking.provider_id != provider_for_user.id:
            raise HTTPException(status_code=403, detail="Only the assigned provider can update this booking.")

        allowed_transitions = {
            BookingStatus.pending: ["accepted", "declined"],
            BookingStatus.accepted: ["completion_requested"],
        }
        allowed = allowed_transitions.get(booking.status, [])
        if requested_status not in allowed:
            raise HTTPException(status_code=400, detail="That booking action is not allowed right now.")

    elif requested_status == "cancelled":
        if booking.resident_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the resident can cancel this booking.")
        if booking.status != BookingStatus.pending:
            raise HTTPException(status_code=400, detail="Only pending bookings can be cancelled.")

    elif requested_status == "completed":
        if booking.resident_id != current_user.id:
            raise HTTPException(status_code=403, detail="Only the resident can confirm job completion.")
        if booking.status != BookingStatus.completion_requested:
            raise HTTPException(
                status_code=400,
                detail="The provider must request completion before you can confirm it.",
            )

    booking.status = BookingStatus(requested_status)
    if data.provider_notes:
        booking.provider_notes = data.provider_notes

    if provider:
        if requested_status == "accepted":
            provider.availability_status = "busy"
        elif requested_status in ["declined", "cancelled", "completed"]:
            other_open = count_open_bookings(db, provider.id, exclude_booking_id=booking_id)
            if other_open == 0:
                provider.availability_status = "available"

    db.commit()
    db.refresh(booking)
    return booking


@router.patch("/provider/availability", response_model=MessageResponse)
def set_provider_availability(
    availability_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role.value != "provider":
        raise HTTPException(status_code=403, detail="Only providers can update availability.")

    valid = ["available", "busy", "offline"]
    if availability_status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Choose from: {valid}")

    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")

    provider.availability_status = availability_status
    db.commit()

    labels = {
        "available": "You are now visible and accepting bookings.",
        "busy": "You are marked as busy.",
        "offline": "You are now offline. Residents cannot create new bookings for you.",
    }
    return {"message": labels[availability_status], "success": True}


@router.get("/{booking_id}", response_model=BookingDetailOut)
def get_booking_by_id(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if current_user.role.value == "admin":
        return booking

    if current_user.role.value == "resident":
        if booking.resident_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        return booking

    if current_user.role.value == "provider":
        provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
        if not provider or booking.provider_id != provider.id:
            raise HTTPException(status_code=403, detail="Access denied.")
        return booking

    raise HTTPException(status_code=403, detail="Access denied.")
