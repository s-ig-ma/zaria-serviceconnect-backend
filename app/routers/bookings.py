# app/routers/bookings.py
# Booking creation, status management, and history

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.models import Booking, Provider, User, BookingStatus, ProviderStatus
from app.schemas.schemas import BookingCreate, BookingStatusUpdate, BookingOut, BookingDetailOut, MessageResponse

router = APIRouter(prefix="/bookings", tags=["Bookings"])


@router.post("/", response_model=BookingOut, status_code=201)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Resident creates a booking request.
    
    - Only residents can create bookings
    - Provider must be approved
    - Booking starts in 'pending' status
    """
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can create bookings.")

    # Check that the provider exists and is approved
    provider = db.query(Provider).filter(
        Provider.id == data.provider_id,
        Provider.status == ProviderStatus.approved
    ).first()

    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found or not available.")

    booking = Booking(
        resident_id=current_user.id,
        provider_id=data.provider_id,
        service_description=data.service_description,
        scheduled_date=data.scheduled_date,
        scheduled_time=data.scheduled_time,
        notes=data.notes,
        status=BookingStatus.pending,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my/resident", response_model=List[BookingDetailOut])
def get_resident_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resident: View all my bookings (booking history screen).
    Returns bookings sorted by newest first.
    """
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provider: View all booking requests sent to me (job history screen).
    """
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


@router.patch("/{booking_id}/status", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    data: BookingStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Provider accepts, declines, or marks a booking complete.
    Resident can cancel their own booking.
    
    Allowed transitions:
    - Provider: pending → accepted, pending → declined
    - Provider: accepted → completed
    - Resident: pending → cancelled
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    role = current_user.role.value

    if role == "provider":
        # Verify this booking belongs to this provider
        provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
        if not provider or booking.provider_id != provider.id:
            raise HTTPException(status_code=403, detail="This booking is not yours.")

        allowed = {
            BookingStatus.pending: [BookingStatus.accepted, BookingStatus.declined],
            BookingStatus.accepted: [BookingStatus.completed],
        }

    elif role == "resident":
        # Resident can only cancel their own pending booking
        if booking.resident_id != current_user.id:
            raise HTTPException(status_code=403, detail="This booking is not yours.")

        allowed = {
            BookingStatus.pending: [BookingStatus.cancelled],
        }
    else:
        raise HTTPException(status_code=403, detail="Not allowed.")

    current_status = booking.status
    if data.status not in allowed.get(current_status, []):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change status from '{current_status.value}' to '{data.status.value}'."
        )

    booking.status = data.status
    if data.provider_notes:
        booking.provider_notes = data.provider_notes

    db.commit()
    db.refresh(booking)
    return booking


@router.get("/admin/all", response_model=List[BookingDetailOut])
def admin_get_all_bookings(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: View all bookings across the platform."""
    return db.query(Booking).order_by(Booking.created_at.desc()).all()


@router.get("/{booking_id}", response_model=BookingDetailOut)
def get_booking_detail(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get full details for a single booking."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Only allow the resident, the provider, or admin to view
    if current_user.role.value == "resident" and booking.resident_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    if current_user.role.value == "provider":
        provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
        if not provider or booking.provider_id != provider.id:
            raise HTTPException(status_code=403, detail="Access denied.")

    return booking
