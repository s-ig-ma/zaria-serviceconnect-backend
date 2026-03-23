# app/routers/reviews.py
# Rating and review system

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.models import Review, Booking, Provider, User, BookingStatus
from app.schemas.schemas import ReviewCreate, ReviewOut

router = APIRouter(prefix="/reviews", tags=["Reviews"])


def _recalculate_provider_rating(provider: Provider, db: Session):
    """
    Helper: Recalculate and update a provider's average rating
    after a new review is added.
    """
    all_reviews = db.query(Review).filter(Review.provider_id == provider.id).all()
    if all_reviews:
        total = sum(r.rating for r in all_reviews)
        provider.average_rating = round(total / len(all_reviews), 1)
        provider.total_reviews = len(all_reviews)
    db.commit()


@router.post("/", response_model=ReviewOut, status_code=201)
def create_review(
    data: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Resident leaves a review after a completed booking.
    
    Rules:
    - Only residents can leave reviews
    - Booking must be in 'completed' status
    - Can only review once per booking
    """
    if current_user.role.value != "resident":
        raise HTTPException(status_code=403, detail="Only residents can leave reviews.")

    # Verify the booking exists and belongs to this resident
    booking = db.query(Booking).filter(
        Booking.id == data.booking_id,
        Booking.resident_id == current_user.id
    ).first()

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.status != BookingStatus.completed:
        raise HTTPException(
            status_code=400,
            detail="You can only review a completed booking."
        )

    # Prevent duplicate reviews for the same booking
    existing_review = db.query(Review).filter(Review.booking_id == data.booking_id).first()
    if existing_review:
        raise HTTPException(status_code=400, detail="You have already reviewed this booking.")

    review = Review(
        booking_id=data.booking_id,
        resident_id=current_user.id,
        provider_id=booking.provider_id,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    db.flush()

    # Update the provider's average rating
    provider = db.query(Provider).filter(Provider.id == booking.provider_id).first()
    if provider:
        _recalculate_provider_rating(provider, db)

    db.commit()
    db.refresh(review)
    return review


@router.get("/provider/{provider_id}", response_model=List[ReviewOut])
def get_provider_reviews(provider_id: int, db: Session = Depends(get_db)):
    """
    Public: Get all reviews for a specific provider.
    These appear on the Provider Profile screen.
    """
    return (
        db.query(Review)
        .filter(Review.provider_id == provider_id)
        .order_by(Review.created_at.desc())
        .all()
    )
