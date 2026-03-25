# app/schemas/schemas.py
# ─────────────────────────────────────────────────────────────────────────────
# Updated schemas — includes latitude/longitude on Provider and auth endpoints
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


class Token(BaseModel):
    access_token : str
    token_type   : str = "bearer"
    role         : str
    user_id      : int
    name         : str


class TokenData(BaseModel):
    email : Optional[str] = None
    role  : Optional[str] = None


class ResidentRegister(BaseModel):
    name     : str      = Field(..., min_length=2, max_length=100)
    email    : EmailStr
    phone    : str      = Field(..., min_length=7, max_length=20)
    password : str      = Field(..., min_length=6)
    location : Optional[str] = None


class ProviderRegister(BaseModel):
    name                : str
    email               : EmailStr
    phone               : str
    password            : str       = Field(..., min_length=6)
    location            : Optional[str] = None
    latitude            : Optional[float] = None   # NEW
    longitude           : Optional[float] = None   # NEW
    category_id         : int
    years_of_experience : int = 0
    description         : Optional[str] = None


class LoginRequest(BaseModel):
    email    : EmailStr
    password : str


class UserOut(BaseModel):
    id            : int
    name          : str
    email         : str
    phone         : str
    location      : Optional[str]
    role          : str
    is_active     : bool
    profile_photo : Optional[str]
    created_at    : datetime

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name        : str
    description : Optional[str] = None
    icon        : Optional[str] = None


class CategoryOut(BaseModel):
    id          : int
    name        : str
    description : Optional[str]
    icon        : Optional[str]
    is_custom   : bool = False

    class Config:
        from_attributes = True


class ProviderOut(BaseModel):
    id                  : int
    user_id             : int
    category_id         : int
    description         : Optional[str]
    years_of_experience : int
    status              : str
    average_rating      : float
    total_reviews       : int
    location            : Optional[str]
    latitude            : Optional[float]   # NEW
    longitude           : Optional[float]   # NEW
    # distance_km is added dynamically by the search endpoint — not in DB
    distance_km         : Optional[float] = None
    created_at          : datetime
    user                : UserOut
    category            : CategoryOut

    class Config:
        from_attributes = True


from app.models.models import ProviderStatus

class ProviderStatusUpdate(BaseModel):
    status : ProviderStatus
    reason : Optional[str] = None


class BookingCreate(BaseModel):
    provider_id         : int
    service_description : str
    scheduled_date      : str
    scheduled_time      : str
    notes               : Optional[str] = None


class BookingStatusUpdate(BaseModel):
    status         : str
    provider_notes : Optional[str] = None


class BookingOut(BaseModel):
    id                  : int
    resident_id         : int
    provider_id         : int
    service_description : str
    scheduled_date      : str
    scheduled_time      : str
    status              : str
    notes               : Optional[str]
    provider_notes      : Optional[str]
    created_at          : datetime

    class Config:
        from_attributes = True


class BookingDetailOut(BookingOut):
    resident : UserOut
    provider : ProviderOut

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    booking_id : int
    rating     : int = Field(..., ge=1, le=5)
    comment    : Optional[str] = None


class ReviewOut(BaseModel):
    id          : int
    booking_id  : int
    resident_id : int
    provider_id : int
    rating      : int
    comment     : Optional[str]
    created_at  : datetime
    resident    : UserOut

    class Config:
        from_attributes = True


class ComplaintCreate(BaseModel):
    booking_id  : int
    message     : str


class ComplaintResolve(BaseModel):
    status          : str
    resolution_note : Optional[str] = None


class ComplaintOut(BaseModel):
    id              : int
    booking_id      : int
    user_id         : int
    provider_id     : int
    message         : str
    status          : str
    resolution_note : Optional[str]
    created_at      : datetime
    user            : UserOut

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message : str
    success : bool = True
