# app/models/models.py

from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, Enum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class UserRole(str, enum.Enum):
    resident = "resident"
    provider = "provider"
    admin    = "admin"


class ProviderStatus(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    suspended = "suspended"


class AvailabilityStatus(str, enum.Enum):
    """
    Provider availability — updated automatically by the booking system:
      available → provider is ready to accept new bookings
      busy      → provider has accepted a booking and is currently working
      offline   → provider has manually set themselves as unavailable
    """
    available = "available"
    busy      = "busy"
    offline   = "offline"


class BookingStatus(str, enum.Enum):
    pending   = "pending"
    accepted  = "accepted"
    completion_requested = "completion_requested"
    completed = "completed"
    cancelled = "cancelled"
    declined  = "declined"


class ComplaintStatus(str, enum.Enum):
    open      = "open"
    in_review = "in_review"
    resolved  = "resolved"


class ComplaintActionType(str, enum.Enum):
    warning = "warning"
    provider_suspension = "provider_suspension"
    account_deactivation = "account_deactivation"
    note = "note"


class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=False)
    email           = Column(String(150), unique=True, index=True, nullable=False)
    phone           = Column(String(20), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    location        = Column(String(200), nullable=True)
    home_address    = Column(String(255), nullable=True)
    role            = Column(Enum(UserRole), default=UserRole.resident, nullable=False)
    is_active       = Column(Boolean, default=True)
    profile_photo   = Column(String(255), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    bookings         = relationship("Booking", back_populates="resident",
                                    foreign_keys="Booking.resident_id")
    reviews          = relationship("Review", back_populates="resident")
    complaints       = relationship("Complaint", back_populates="user")
    provider_profile = relationship("Provider", back_populates="user", uselist=False)
    sent_messages    = relationship(
        "Message",
        back_populates="sender",
        foreign_keys="Message.sender_user_id",
    )
    received_messages = relationship(
        "Message",
        back_populates="recipient",
        foreign_keys="Message.recipient_user_id",
    )
    notifications = relationship("Notification", back_populates="user")
    complaint_actions_created = relationship(
        "ComplaintAction",
        back_populates="admin_user",
        foreign_keys="ComplaintAction.admin_user_id",
    )
    complaint_actions_received = relationship(
        "ComplaintAction",
        back_populates="target_user",
        foreign_keys="ComplaintAction.target_user_id",
    )


class Category(Base):
    __tablename__ = "categories"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    icon        = Column(String(100), nullable=True)
    is_custom   = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    providers = relationship("Provider", back_populates="category")


class Provider(Base):
    __tablename__ = "providers"

    id                  = Column(Integer, primary_key=True, index=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    category_id         = Column(Integer, ForeignKey("categories.id"), nullable=True)
    service_name        = Column(String(150), nullable=True)
    description         = Column(Text, nullable=True)
    years_of_experience = Column(Integer, default=0)
    passport_photo_path = Column(String(255), nullable=True)
    id_document_path    = Column(String(255), nullable=True)
    skill_proof_path    = Column(String(255), nullable=True)
    has_shop_in_zaria   = Column(Boolean, default=False)
    shop_address        = Column(String(255), nullable=True)
    status              = Column(Enum(ProviderStatus), default=ProviderStatus.pending)
    average_rating      = Column(Float, default=0.0)
    total_reviews       = Column(Integer, default=0)
    location            = Column(String(200), nullable=True)
    latitude            = Column(Float, nullable=True)
    longitude           = Column(Float, nullable=True)

    # NEW: Availability status
    # Default = available when provider registers
    # Changes automatically when they accept/complete bookings
    availability_status = Column(
        String(20),
        default  = "available",
        nullable = False,
        server_default = "available"
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user       = relationship("User", back_populates="provider_profile")
    category   = relationship("Category", back_populates="providers")
    bookings   = relationship("Booking", back_populates="provider",
                              foreign_keys="Booking.provider_id")
    reviews    = relationship("Review", back_populates="provider")
    complaints = relationship("Complaint", back_populates="provider")


class Booking(Base):
    __tablename__ = "bookings"

    id                  = Column(Integer, primary_key=True, index=True)
    resident_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id         = Column(Integer, ForeignKey("providers.id"), nullable=False)
    service_description = Column(Text, nullable=False)
    scheduled_date      = Column(String(50), nullable=False)
    scheduled_time      = Column(String(20), nullable=False)
    service_address     = Column(String(255), nullable=True)
    status              = Column(Enum(BookingStatus), default=BookingStatus.pending)
    notes               = Column(Text, nullable=True)
    provider_notes      = Column(Text, nullable=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), onupdate=func.now())

    resident  = relationship("User", back_populates="bookings", foreign_keys=[resident_id])
    provider  = relationship("Provider", back_populates="bookings", foreign_keys=[provider_id])
    review    = relationship("Review", back_populates="booking", uselist=False)
    complaint = relationship("Complaint", back_populates="booking", uselist=False)


class Review(Base):
    __tablename__ = "reviews"

    id          = Column(Integer, primary_key=True, index=True)
    booking_id  = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True)
    resident_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("providers.id"), nullable=False)
    rating      = Column(Integer, nullable=False)
    comment     = Column(Text, nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    booking  = relationship("Booking", back_populates="review")
    resident = relationship("User", back_populates="reviews")
    provider = relationship("Provider", back_populates="reviews")


class Complaint(Base):
    __tablename__ = "complaints"

    id              = Column(Integer, primary_key=True, index=True)
    booking_id      = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider_id     = Column(Integer, ForeignKey("providers.id"), nullable=False)
    message         = Column(Text, nullable=False)
    status          = Column(Enum(ComplaintStatus), default=ComplaintStatus.open)
    resolution_note = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    booking  = relationship("Booking", back_populates="complaint")
    user     = relationship("User", back_populates="complaints")
    provider = relationship("Provider", back_populates="complaints")
    messages = relationship("Message", back_populates="complaint")
    actions = relationship("ComplaintAction", back_populates="complaint")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=True)
    sender_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="messages")
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_user_id])
    recipient = relationship("User", back_populates="received_messages", foreign_keys=[recipient_user_id])


class ComplaintAction(Base):
    __tablename__ = "complaint_actions"

    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"), nullable=False)
    admin_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(Enum(ComplaintActionType), nullable=False)
    note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    complaint = relationship("Complaint", back_populates="actions")
    admin_user = relationship("User", back_populates="complaint_actions_created", foreign_keys=[admin_user_id])
    target_user = relationship("User", back_populates="complaint_actions_received", foreign_keys=[target_user_id])


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    type = Column(String(50), nullable=False, default="general", server_default="general")
    related_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, server_default="0")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
