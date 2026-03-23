# app/schemas/complaint_schemas.py
# ─────────────────────────────────────────────────────────────────────────────
# Pydantic schemas for the complaint system.
# These define the shape of data coming IN (requests) and going OUT (responses).
# ─────────────────────────────────────────────────────────────────────────────

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── What the resident sends when submitting a complaint ───────────────────────
class ComplaintCreate(BaseModel):
    booking_id : int  = Field(..., example=1,
                              description="ID of the booking this complaint is about")
    message    : str  = Field(..., min_length=10, example="The provider arrived 3 hours late "
                              "and did not complete the work properly.")


# ── What the admin sends when resolving a complaint ───────────────────────────
class ComplaintResolve(BaseModel):
    status          : str           = Field(..., example="resolved",
                                            description="One of: open, in_review, resolved")
    resolution_note : Optional[str] = Field(None,
                                            example="We have warned the provider. "
                                            "A refund has been processed.")


# ── Nested user info inside complaint response ────────────────────────────────
class UserBasic(BaseModel):
    id    : int
    name  : str
    email : str
    phone : str

    class Config:
        from_attributes = True


# ── Nested provider info inside complaint response ────────────────────────────
class ProviderBasic(BaseModel):
    id       : int
    user     : UserBasic

    class Config:
        from_attributes = True


# ── Full complaint response returned by the API ───────────────────────────────
class ComplaintOut(BaseModel):
    id              : int
    booking_id      : int
    user_id         : int
    provider_id     : int
    message         : str
    status          : str
    resolution_note : Optional[str]
    created_at      : datetime
    # Nested info so the frontend doesn't need extra API calls
    user            : UserBasic
    provider        : ProviderBasic

    class Config:
        from_attributes = True


# ── Simple success message response ──────────────────────────────────────────
class MessageResponse(BaseModel):
    message : str
    success : bool = True
