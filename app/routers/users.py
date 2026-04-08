# app/routers/users.py
# User management (admin only) + user self-service

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.models import User
from app.schemas.schemas import MessageResponse, ResidentProfileUpdate, UserOut
from app.utils.uploads import save_upload

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserOut)
def get_my_user_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserOut)
def update_my_profile(
    name: str | None = Form(None),
    phone: str | None = Form(None),
    location: str | None = Form(None),
    home_address: str | None = Form(None),
    profile_photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update = ResidentProfileUpdate(
        name=name,
        phone=phone,
        location=location,
        home_address=home_address,
    )

    if update.name is not None:
        current_user.name = update.name.strip()
    if update.phone is not None:
        current_user.phone = update.phone.strip()
    if update.location is not None:
        current_user.location = update.location.strip() or None
    if update.home_address is not None:
        current_user.home_address = update.home_address.strip() or None

    if profile_photo is not None:
        current_user.profile_photo = save_upload(
            profile_photo, "profiles", f"user_{current_user.id}"
        )

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/admin/all", response_model=List[UserOut])
def admin_get_all_users(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Get all registered users (residents + providers)."""
    return db.query(User).all()


@router.get("/admin/{user_id}", response_model=UserOut)
def admin_get_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Get details for a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/admin/{user_id}/deactivate", response_model=MessageResponse)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Deactivate (ban) a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()
    return {"message": f"User '{user.name}' has been deactivated.", "success": True}


@router.patch("/admin/{user_id}/activate", response_model=MessageResponse)
def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin: Reactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = True
    db.commit()
    return {"message": f"User '{user.name}' has been reactivated.", "success": True}
