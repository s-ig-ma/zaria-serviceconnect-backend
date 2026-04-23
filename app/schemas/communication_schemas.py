from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.schemas import UserOut


class MessageCreate(BaseModel):
    recipient_user_id: Optional[int] = None
    content: str = Field(..., min_length=1)
    complaint_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    complaint_id: Optional[int]
    sender_user_id: int
    recipient_user_id: int
    content: str
    is_read: bool
    created_at: datetime
    sender: UserOut
    recipient: UserOut

    class Config:
        from_attributes = True


class ComplaintActionCreate(BaseModel):
    action_type: str
    target_user_id: Optional[int] = None
    note: Optional[str] = None


class ComplaintActionOut(BaseModel):
    id: int
    complaint_id: int
    admin_user_id: int
    target_user_id: Optional[int]
    action_type: str
    note: Optional[str]
    created_at: datetime
    admin_user: UserOut
    target_user: Optional[UserOut] = None

    class Config:
        from_attributes = True


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    type: str
    related_id: Optional[int]
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DeviceTokenRegister(BaseModel):
    token: str = Field(..., min_length=20)
    device_name: Optional[str] = None


class DeviceTokenRemove(BaseModel):
    token: str = Field(..., min_length=20)
