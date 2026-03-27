# app/routers/bookings.py
# ─────────────────────────────────────────────────────────────────────────────
# BOOKINGS API
#
# Availability auto-update rules:
#   Provider accepts booking  → availability_status = "busy"
#   Booking completed         → availability_status = "available"
#   Booking declined/cancelled→ availability_status stays unchanged
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import Booking, Provider, User, BookingStatus
from app.schemas.schemas import (
    BookingCreate, BookingStatusUpdate,
    BookingOut, BookingDetailOut, MessageResponse
)

router = APIRouter(prefix="/bookings", tags=["Bookings"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /bookings/
# Resident creates a new booking request
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/", response_model=BookingDetailOut, status_code=201)
def create_booking(
    data         : BookingCreate,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can create bookings.")

    provider = db.query(Provider).filter(Provider.id == data.provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    if provider.status.value != "approved":
        raise HTTPException(status_code=400, detail="Provider is not approved.")

    booking = Booking(
        resident_id         = current_user.id,
        provider_id         = data.provider_id,
        service_description = data.service_description,
        scheduled_date      = data.scheduled_date,
        scheduled_time      = data.scheduled_time,
        notes               = data.notes,
        status              = BookingStatus.pending
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


# ─────────────────────────────────────────────────────────────────────────────
# GET /bookings/my/resident
# Resident views their own bookings
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/my/resident", response_model=List[BookingDetailOut])
def get_resident_bookings(
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can access this.")
    return (
        db.query(Booking)
        .filter(Booking.resident_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /bookings/my/provider
# Provider views their own bookings
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/my/provider", response_model=List[BookingDetailOut])
def get_provider_bookings(
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    if current_user.role.value != "provider":
        raise HTTPException(status_code=403, detail="Only providers can access this.")

    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")

    return (
        db.query(Booking)
        .filter(Booking.provider_id == provider.id)
        .order_by(Booking.created_at.desc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /bookings/{id}/status
# Update booking status — also auto-updates provider availability
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/{booking_id}/status", response_model=BookingDetailOut)
def update_booking_status(
    booking_id   : int,
    data         : BookingStatusUpdate,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    """
    Update a booking's status.

    Availability auto-update logic:
      - Provider accepts  → provider becomes BUSY
      - Booking completed → provider becomes AVAILABLE again
      - Booking declined  → provider stays AVAILABLE (they are free)
      - Booking cancelled → provider stays AVAILABLE

    This ensures the availability badge always reflects reality.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # Validate the new status
    valid_statuses = ["accepted", "completed", "cancelled", "declined"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {valid_statuses}"
        )

    # Permission checks
    if data.status in ["accepted", "completed", "declined"]:
        # Only the provider can accept, complete, or decline
        provider = db.query(Provider).filter(
            Provider.user_id == current_user.id
        ).first()
        if not provider or booking.provider_id != provider.id:
            raise HTTPException(
                status_code=403,
                detail="Only the assigned provider can update this booking."
            )
    elif data.status == "cancelled":
        # Only the resident can cancel
        if booking.resident_id != current_user.id:
            raise HTTPException(
                status_code=403,
                detail="Only the resident can cancel this booking."
            )

    # Update booking status
    booking.status = data.status
    if data.provider_notes:
        booking.provider_notes = data.provider_notes

    # ── AUTO-UPDATE PROVIDER AVAILABILITY ─────────────────────────────────────
    provider = db.query(Provider).filter(
        Provider.id == booking.provider_id
    ).first()

    if provider:
        if data.status == "accepted":
            # Provider accepted — they are now busy
            provider.availability_status = "busy"

        elif data.status in ["completed", "declined", "cancelled"]:
            # Booking is done or cancelled — provider is free again
            # Check if provider has any other active (accepted) bookings
            other_active = db.query(Booking).filter(
                Booking.provider_id == provider.id,
                Booking.id          != booking_id,
                Booking.status      == "accepted"
            ).first()

            if not other_active:
                # No other active bookings — mark as available
                provider.availability_status = "available"
            # If they have other active bookings, stay busy

    db.commit()
    db.refresh(booking)
    return booking


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /bookings/provider/availability
# Provider manually sets their availability (e.g. going offline for the day)
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/provider/availability", response_model=MessageResponse)
def set_provider_availability(
    availability_status : str,
    db                  : Session = Depends(get_db),
    current_user        : User    = Depends(get_current_user)
):
    """
    Provider manually updates their availability status.
    Useful for going offline when not working.

    Valid values: available, busy, offline
    """
    if current_user.role.value != "provider":
        raise HTTPException(status_code=403, detail="Only providers can update availability.")

    valid = ["available", "busy", "offline"]
    if availability_status not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {valid}"
        )

    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")

    provider.availability_status = availability_status
    db.commit()

    labels = {
        "available": "You are now visible and accepting bookings.",
        "busy"     : "You are marked as busy.",
        "offline"  : "You are now offline. You won't appear in search results."
    }
    return {"message": labels[availability_status], "success": True}
