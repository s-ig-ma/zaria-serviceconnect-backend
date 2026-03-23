# app/routers/complaints.py
# ─────────────────────────────────────────────────────────────────────────────
# COMPLAINT SYSTEM API ENDPOINTS
#
# Endpoints:
#   POST /complaints              — resident submits a complaint
#   GET  /complaints/my           — resident views their own complaints
#   GET  /complaints              — admin views ALL complaints
#   PUT  /complaints/{id}/resolve — admin resolves a complaint
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.models import Complaint, Booking, Provider, User, ComplaintStatus, BookingStatus
from app.schemas.complaint_schemas import (
    ComplaintCreate, ComplaintResolve, ComplaintOut, MessageResponse
)

router = APIRouter(prefix="/complaints", tags=["Complaints"])


# ─────────────────────────────────────────────────────────────────────────────
# POST /complaints
# Resident submits a complaint about a completed booking.
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/", response_model=ComplaintOut, status_code=201)
def submit_complaint(
    data       : ComplaintCreate,
    db         : Session = Depends(get_db),
    current_user: User   = Depends(get_current_user)
):
    """
    Submit a complaint about a booking.

    Rules:
    - Only residents can submit complaints
    - The booking must belong to the logged-in resident
    - Each booking can only have ONE complaint
    - The booking does NOT need to be completed (resident can complain about
      any booking — pending, accepted, or completed)
    """
    # Only residents can file complaints
    if current_user.role.value != "resident":
        raise HTTPException(
            status_code=403,
            detail="Only residents can submit complaints."
        )

    # Find the booking and verify it belongs to this resident
    booking = db.query(Booking).filter(
        Booking.id          == data.booking_id,
        Booking.resident_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found. You can only complain about your own bookings."
        )

    # Check if a complaint already exists for this booking
    existing = db.query(Complaint).filter(
        Complaint.booking_id == data.booking_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="A complaint has already been submitted for this booking."
        )

    # Create the complaint
    complaint = Complaint(
        booking_id  = data.booking_id,
        user_id     = current_user.id,
        provider_id = booking.provider_id,
        message     = data.message,
        status      = ComplaintStatus.open,
    )
    db.add(complaint)
    db.commit()
    db.refresh(complaint)
    return complaint


# ─────────────────────────────────────────────────────────────────────────────
# GET /complaints/my
# Resident views their own complaints and their statuses.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/my", response_model=List[ComplaintOut])
def get_my_complaints(
    db          : Session = Depends(get_db),
    current_user: User    = Depends(get_current_user)
):
    """
    Returns all complaints submitted by the logged-in resident.
    The resident can see status updates and resolution notes from admin.
    """
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can access this.")

    return (
        db.query(Complaint)
        .filter(Complaint.user_id == current_user.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /complaints
# Admin views all complaints across the platform.
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[ComplaintOut])
def get_all_complaints(
    status : Optional[str] = Query(None,
                description="Filter by status: open, in_review, resolved"),
    db     : Session = Depends(get_db),
    admin  : User    = Depends(get_current_admin)
):
    """
    Admin: View all complaints on the platform.
    Can optionally filter by status.

    Example:
      GET /complaints           → all complaints
      GET /complaints?status=open   → only open complaints
      GET /complaints?status=resolved → only resolved
    """
    query = db.query(Complaint)

    if status:
        # Validate the status value
        valid_statuses = ["open", "in_review", "resolved"]
        if status not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Choose from: {valid_statuses}"
            )
        query = query.filter(Complaint.status == status)

    return query.order_by(Complaint.created_at.desc()).all()


# ─────────────────────────────────────────────────────────────────────────────
# PUT /complaints/{id}/resolve
# Admin updates complaint status and optionally adds a resolution note.
# ─────────────────────────────────────────────────────────────────────────────
@router.put("/{complaint_id}/resolve", response_model=ComplaintOut)
def resolve_complaint(
    complaint_id : int,
    data         : ComplaintResolve,
    db           : Session = Depends(get_db),
    admin        : User    = Depends(get_current_admin)
):
    """
    Admin: Update complaint status and add a resolution note.

    Status transitions:
      open → in_review  (admin starts reviewing)
      in_review → resolved  (admin resolves it)
      Any status can be set directly.

    If status is 'resolved', admin can provide a resolution_note
    which the resident will see in their complaint history.
    """
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    # Validate status
    valid_statuses = ["open", "in_review", "resolved"]
    if data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Choose from: {valid_statuses}"
        )

    # Update the complaint
    complaint.status = data.status

    if data.resolution_note:
        complaint.resolution_note = data.resolution_note

    db.commit()
    db.refresh(complaint)
    return complaint


# ─────────────────────────────────────────────────────────────────────────────
# GET /complaints/{id}
# Get a single complaint by ID (admin or the resident who filed it).
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{complaint_id}", response_model=ComplaintOut)
def get_complaint(
    complaint_id : int,
    db           : Session = Depends(get_db),
    current_user : User    = Depends(get_current_user)
):
    """Get a single complaint by ID."""
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found.")

    # Residents can only see their own complaints
    if (current_user.role.value == "resident" and
            complaint.user_id != current_user.id):
        raise HTTPException(status_code=403, detail="Access denied.")

    return complaint
