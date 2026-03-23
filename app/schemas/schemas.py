# app/schemas/schemas.py
# Pydantic models define the shape of data for API requests and responses.
# They validate input and serialize output automatically.

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import datetime
from app.models.models import UserRole, ProviderStatus, BookingStatus, ComplaintStatus


# ─── Token Schemas ─────────────────────────────────────────────────────────────

class Token(BaseModel):
    """Response after successful login."""
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: int
    name: str


class TokenData(BaseModel):
    """Data extracted from JWT token."""
    email: Optional[str] = None
    role: Optional[str] = None


# ─── User Schemas ──────────────────────────────────────────────────────────────

class ResidentRegister(BaseModel):
    """Fields required to register as a resident."""
    name: str = Field(..., min_length=2, max_length=100, example="Aminu Musa")
    email: EmailStr = Field(..., example="aminu@example.com")
    phone: str = Field(..., min_length=7, max_length=20, example="+2348012345678")
    password: str = Field(..., min_length=6, example="securepassword")
    location: Optional[str] = Field(None, example="Sabon Gari, Zaria")


class ProviderRegister(BaseModel):
    """Fields required to register as a service provider."""
    name: str = Field(..., min_length=2, max_length=100, example="Usman Plumber")
    email: EmailStr = Field(..., example="usman@example.com")
    phone: str = Field(..., min_length=7, max_length=20, example="+2348098765432")
    password: str = Field(..., min_length=6, example="securepassword")
    location: Optional[str] = Field(None, example="Tudun Wada, Zaria")
    category_id: int = Field(..., example=1)
    years_of_experience: int = Field(default=0, ge=0, example=5)
    description: Optional[str] = Field(None, example="Experienced plumber with 5 years of work in Zaria")


class LoginRequest(BaseModel):
    """Login credentials."""
    email: EmailStr
    password: str


class AdminLogin(BaseModel):
    """Admin login credentials."""
    email: EmailStr
    password: str


class UserOut(BaseModel):
    """User data returned in API responses (password excluded)."""
    id: int
    name: str
    email: str
    phone: str
    location: Optional[str]
    role: str
    is_active: bool
    profile_photo: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True  # Allows reading from SQLAlchemy models


# ─── Category Schemas ──────────────────────────────────────────────────────────

class CategoryCreate(BaseModel):
    name: str = Field(..., example="Plumbing")
    description: Optional[str] = Field(None, example="Pipe installation and repair services")
    icon: Optional[str] = Field(None, example="plumbing_icon")


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]

    class Config:
        from_attributes = True


# ─── Provider Schemas ──────────────────────────────────────────────────────────

class ProviderOut(BaseModel):
    """Full provider profile returned in API responses."""
    id: int
    user_id: int
    category_id: int
    description: Optional[str]
    years_of_experience: int
    status: str
    average_rating: float
    total_reviews: int
    location: Optional[str]
    created_at: datetime
    # Nested user info
    user: UserOut
    # Nested category info
    category: CategoryOut

    class Config:
        from_attributes = True


class ProviderStatusUpdate(BaseModel):
    """Used by admin to change provider approval status."""
    status: ProviderStatus
    reason: Optional[str] = None  # Optional reason for rejection/suspension


# ─── Booking Schemas ───────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    """Data needed to create a new booking."""
    provider_id: int = Field(..., example=1)
    service_description: str = Field(..., example="Fix leaking pipe in kitchen")
    scheduled_date: str = Field(..., example="2024-06-15")
    scheduled_time: str = Field(..., example="10:00 AM")
    notes: Optional[str] = Field(None, example="Please bring your own tools")


class BookingStatusUpdate(BaseModel):
    """Used by provider to accept/decline a booking."""
    status: BookingStatus
    provider_notes: Optional[str] = None


class BookingOut(BaseModel):
    """Booking data returned in responses."""
    id: int
    resident_id: int
    provider_id: int
    service_description: str
    scheduled_date: str
    scheduled_time: str
    status: str
    notes: Optional[str]
    provider_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class BookingDetailOut(BookingOut):
    """Booking with full resident and provider details."""
    resident: UserOut
    provider: ProviderOut

    class Config:
        from_attributes = True


# ─── Review Schemas ────────────────────────────────────────────────────────────

class ReviewCreate(BaseModel):
    """Data needed to leave a review."""
    booking_id: int = Field(..., example=1)
    rating: int = Field(..., ge=1, le=5, example=4)
    comment: Optional[str] = Field(None, example="Great service, very professional!")


class ReviewOut(BaseModel):
    id: int
    booking_id: int
    resident_id: int
    provider_id: int
    rating: int
    comment: Optional[str]
    created_at: datetime
    resident: UserOut

    class Config:
        from_attributes = True


# ─── Complaint Schemas ─────────────────────────────────────────────────────────

class ComplaintCreate(BaseModel):
    """Data needed to submit a complaint."""
    booking_id: int = Field(..., example=1)
    subject: str = Field(..., example="Provider did not show up")
    description: str = Field(..., example="I waited 3 hours and the provider never arrived")


class ComplaintUpdate(BaseModel):
    """Admin response to a complaint."""
    status: ComplaintStatus
    admin_response: Optional[str] = None


class ComplaintOut(BaseModel):
    id: int
    booking_id: int
    resident_id: int
    provider_id: int
    subject: str
    description: str
    status: str
    admin_response: Optional[str]
    created_at: datetime
    resident: UserOut

    class Config:
        from_attributes = True


# ─── General Response ──────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    """A simple message response for operations that don't return data."""
    message: str
    success: bool = True
