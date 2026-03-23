# app/routers/providers.py
# ─────────────────────────────────────────────────────────────────────────────
# PROVIDERS API — includes global search endpoint
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.models import Provider, User, Category, ProviderStatus
from app.schemas.schemas import ProviderOut, ProviderStatusUpdate, MessageResponse

router = APIRouter(prefix="/providers", tags=["Providers"])


# ─────────────────────────────────────────────────────────────────────────────
# GET /providers/search?q=
# Global search — searches provider name, category name, and description
# Must be defined BEFORE /{provider_id} route to avoid route conflicts
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/search", response_model=List[ProviderOut])
def search_providers(
    q  : str     = Query(..., min_length=1,
                         description="Search query — matches name, category, or description"),
    db : Session = Depends(get_db)
):
    """
    Search for approved providers by:
    - Provider name       (e.g. search "Moses" finds provider named Moses)
    - Service category    (e.g. search "plumb" finds Plumbing providers)
    - Service description (e.g. search "pipe" finds providers who mention pipes)

    Returns results ordered by rating (best rated first).

    Example calls:
      GET /providers/search?q=Moses
      GET /providers/search?q=plumber
      GET /providers/search?q=electrical
      GET /providers/search?q=Sabon Gari
    """
    search_term = f"%{q.lower()}%"

    results = (
        db.query(Provider)
        .join(Provider.user)       # join users table for name search
        .join(Provider.category)   # join categories table for category name search
        .filter(
            Provider.status == ProviderStatus.approved,
            or_(
                # Search provider's full name (case-insensitive)
                User.name.ilike(search_term),

                # Search service category name
                Category.name.ilike(search_term),

                # Search provider's description / bio
                Provider.description.ilike(search_term),

                # Search provider's location
                Provider.location.ilike(search_term),
            )
        )
        .order_by(Provider.average_rating.desc())
        .all()
    )

    return results


# ─────────────────────────────────────────────────────────────────────────────
# GET /providers/
# Browse all approved providers, optionally filtered by category
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_model=List[ProviderOut])
def get_providers(
    category_id : Optional[int] = Query(None,
                                        description="Filter by category ID"),
    db          : Session       = Depends(get_db)
):
    """
    Returns all approved providers.
    Optionally filter by category_id.
    """
    query = db.query(Provider).filter(
        Provider.status == ProviderStatus.approved
    )
    if category_id:
        query = query.filter(Provider.category_id == category_id)

    return query.order_by(Provider.average_rating.desc()).all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /providers/me/profile
# Provider views their own profile
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/me/profile", response_model=ProviderOut)
def get_my_provider_profile(
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")
    return provider


# ─────────────────────────────────────────────────────────────────────────────
# GET /providers/admin/all
# Admin views all providers regardless of status
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/admin/all", response_model=List[ProviderOut])
def admin_get_all_providers(
    db    : Session = Depends(get_db),
    admin : User    = Depends(get_current_admin)
):
    return db.query(Provider).order_by(Provider.created_at.desc()).all()


# ─────────────────────────────────────────────────────────────────────────────
# GET /providers/{provider_id}
# Get a single provider's profile
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider_by_id(
    provider_id : int,
    db          : Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.id     == provider_id,
        Provider.status == ProviderStatus.approved
    ).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    return provider


# ─────────────────────────────────────────────────────────────────────────────
# PATCH /providers/{provider_id}/status
# Admin approves, rejects, or suspends a provider
# ─────────────────────────────────────────────────────────────────────────────
@router.patch("/{provider_id}/status", response_model=MessageResponse)
def update_provider_status(
    provider_id : int,
    data        : ProviderStatusUpdate,
    db          : Session = Depends(get_db),
    admin       : User    = Depends(get_current_admin)
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")

    provider.status = data.status
    db.commit()

    status_messages = {
        "approved"  : "Provider has been approved and is now visible to residents.",
        "rejected"  : "Provider registration has been rejected.",
        "suspended" : "Provider has been suspended.",
        "pending"   : "Provider status set back to pending."
    }
    msg = status_messages.get(data.status.value, f"Status updated to {data.status.value}.")
    return {"message": msg, "success": True}
