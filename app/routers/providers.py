# app/routers/providers.py
# IMPORTANT: Fixed route ordering — all /me/* routes MUST come before /{provider_id}

import math
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_admin
from app.models.models import Provider, User, Category, ProviderStatus
from app.schemas.schemas import ProviderOut, ProviderStatusUpdate, MessageResponse

router = APIRouter(prefix="/providers", tags=["Providers"])


def haversine_distance(lat1, lon1, lat2, lon2):
    R      = 6371.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat   = math.radians(lat2 - lat1)
    dlon   = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)


def _sort_by_distance(providers, user_lat, user_lon):
    if user_lat is not None and user_lon is not None:
        for provider in providers:
            if provider.latitude is not None and provider.longitude is not None:
                provider.distance_km = haversine_distance(
                    user_lat, user_lon, provider.latitude, provider.longitude)
            else:
                provider.distance_km = 99999.0
        providers.sort(key=lambda p: p.distance_km or 99999.0)
        for provider in providers:
            if provider.distance_km == 99999.0:
                provider.distance_km = None
    else:
        providers.sort(key=lambda p: p.average_rating, reverse=True)
        for provider in providers:
            provider.distance_km = None
    return providers


# 1. /search — fixed path, must be first
@router.get("/search", response_model=List[ProviderOut])
def search_providers(
    q        : str             = Query(..., min_length=1),
    user_lat : Optional[float] = Query(None),
    user_lon : Optional[float] = Query(None),
    db       : Session         = Depends(get_db)
):
    search_term = f"%{q.lower()}%"
    results = (
        db.query(Provider)
        .join(Provider.user)
        .outerjoin(Provider.category)
        .filter(
            Provider.status == ProviderStatus.approved,
            or_(
                User.name.ilike(search_term),
                Category.name.ilike(search_term),
                Provider.service_name.ilike(search_term),
                Provider.description.ilike(search_term),
                Provider.location.ilike(search_term),
            )
        )
        .all()
    )
    return _sort_by_distance(results, user_lat, user_lon)


# 2. /me/profile — fixed path, must be before /{provider_id}
@router.get("/me/profile", response_model=ProviderOut)
def get_my_provider_profile(
    current_user : User    = Depends(get_current_user),
    db           : Session = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")
    return provider


# 3. /me/location — fixed path, MUST be before /{provider_id}
@router.patch("/me/location", response_model=MessageResponse)
def update_my_location(
    latitude      : float          = Query(...),
    longitude     : float          = Query(...),
    location_text : Optional[str]  = Query(None),
    current_user  : User           = Depends(get_current_user),
    db            : Session        = Depends(get_db)
):
    provider = db.query(Provider).filter(
        Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")
    provider.latitude  = latitude
    provider.longitude = longitude
    if location_text:
        provider.location = location_text
    db.commit()
    return {"message": "Location updated successfully.", "success": True}


# 4. /admin/all — fixed path
@router.get("/admin/all", response_model=List[ProviderOut])
def admin_get_all_providers(
    db    : Session = Depends(get_db),
    admin : User    = Depends(get_current_admin)
):
    return db.query(Provider).order_by(Provider.created_at.desc()).all()


# 5. / — root path
@router.get("/", response_model=List[ProviderOut])
def get_providers(
    category_id : Optional[int]   = Query(None),
    user_lat    : Optional[float]  = Query(None),
    user_lon    : Optional[float]  = Query(None),
    db          : Session          = Depends(get_db)
):
    query = db.query(Provider).filter(Provider.status == ProviderStatus.approved)
    if category_id:
        query = query.filter(Provider.category_id == category_id)
    results = query.all()
    return _sort_by_distance(results, user_lat, user_lon)


# 6. /{provider_id} — parameter path, MUST be last
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


# 7. /{provider_id}/status
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
    from app.models.models import ProviderStatus as PS
    provider.status = PS(data.status)
    db.commit()
    messages = {
        "approved"  : "Provider approved and is now visible to residents.",
        "rejected"  : "Provider registration rejected.",
        "suspended" : "Provider suspended.",
        "pending"   : "Provider set back to pending."
    }
    return {
        "message": messages.get(data.status, f"Status updated to {data.status}."),
        "success": True
    }
