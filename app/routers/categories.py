# app/routers/categories.py
# Manages service categories (Plumbing, Electrical, etc.)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_admin
from app.models.models import Category, User
from app.schemas.schemas import CategoryCreate, CategoryOut, MessageResponse

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/", response_model=List[CategoryOut])
def get_all_categories(db: Session = Depends(get_db)):
    """
    Public endpoint — returns all service categories.
    Used by the mobile app to show the category browsing screen.
    """
    return db.query(Category).all()


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a single category by ID."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    return category


@router.post("/", response_model=CategoryOut, status_code=201)
def create_category(
    data: CategoryCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin only: Create a new service category."""
    existing = db.query(Category).filter(Category.name == data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists.")

    category = Category(name=data.name, description=data.description, icon=data.icon)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", response_model=MessageResponse)
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """Admin only: Delete a category."""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found.")
    db.delete(category)
    db.commit()
    return {"message": "Category deleted.", "success": True}
