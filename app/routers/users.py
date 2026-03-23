# app/routers/users.py
# User management (admin only) + user self-service

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.models import User
from app.schemas.schemas import UserOut, MessageResponse

router = APIRouter(prefix="/users", tags=["Users"])


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
