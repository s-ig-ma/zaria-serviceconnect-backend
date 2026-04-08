# app/routers/providers.py
# IMPORTANT: Fixed route ordering - all /me/* routes MUST come before /{provider_id}

import math
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.models.models import Category, Provider, ProviderStatus, User
from app.schemas.schemas import MessageResponse, ProviderOut, ProviderStatusUpdate
from app.utils.uploads import save_upload

router = APIRouter(prefix="/providers", tags=["Providers"])


def haversine_distance(lat1, lon1, lat2, lon2):
    radius = 6371.0
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    value = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon / 2) ** 2
    )
    return round(radius * (2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))), 2)


def _sort_by_distance(providers, user_lat, user_lon):
    if user_lat is not None and user_lon is not None:
        for provider in providers:
            if provider.latitude is not None and provider.longitude is not None:
                provider.distance_km = haversine_distance(
                    user_lat, user_lon, provider.latitude, provider.longitude
                )
            else:
                provider.distance_km = 99999.0
        providers.sort(key=lambda provider: provider.distance_km or 99999.0)
        for provider in providers:
            if provider.distance_km == 99999.0:
                provider.distance_km = None
    else:
        providers.sort(key=lambda provider: provider.average_rating, reverse=True)
        for provider in providers:
            provider.distance_km = None
    return providers


def _approved_provider_query(db: Session):
    return db.query(Provider).filter(Provider.status == ProviderStatus.approved)


@router.get("/search", response_model=List[ProviderOut])
def search_providers(
    q: str = Query(..., min_length=1),
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    search_term = f"%{q.lower()}%"
    results = (
        _approved_provider_query(db)
        .join(Provider.user)
        .outerjoin(Provider.category)
        .filter(
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


@router.get("/me/profile", response_model=ProviderOut)
def get_my_provider_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")
    return provider


@router.patch("/me/profile", response_model=ProviderOut)
def update_my_provider_profile(
    name: str | None = Form(None),
    phone: str | None = Form(None),
    location: str | None = Form(None),
    service_name: str | None = Form(None),
    category_id: int | None = Form(None),
    years_of_experience: int | None = Form(None),
    description: str | None = Form(None),
    has_shop_in_zaria: bool | None = Form(None),
    shop_address: str | None = Form(None),
    profile_photo: UploadFile | None = File(None),
    passport_photo: UploadFile | None = File(None),
    id_document: UploadFile | None = File(None),
    skill_proof: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")

    if name is not None:
        current_user.name = name.strip()
    if phone is not None:
        current_user.phone = phone.strip()
    if location is not None:
        clean_location = location.strip() or None
        current_user.location = clean_location
        provider.location = clean_location
    if service_name is not None:
        provider.service_name = service_name.strip() or None
    if category_id is not None:
        provider.category_id = category_id
    if years_of_experience is not None:
        provider.years_of_experience = years_of_experience
    if description is not None:
        provider.description = description.strip() or None
    if has_shop_in_zaria is not None:
        provider.has_shop_in_zaria = has_shop_in_zaria
        if not has_shop_in_zaria:
            provider.shop_address = None
    if shop_address is not None:
        clean_shop_address = shop_address.strip() or None
        if provider.has_shop_in_zaria and not clean_shop_address:
            raise HTTPException(status_code=400, detail="Please enter the shop address in Zaria.")
        provider.shop_address = clean_shop_address

    if profile_photo is not None:
        current_user.profile_photo = save_upload(
            profile_photo, "profiles", f"user_{current_user.id}"
        )
    if passport_photo is not None:
        provider.passport_photo_path = save_upload(
            passport_photo, "verification", f"provider_{provider.id}_passport"
        )
    if id_document is not None:
        provider.id_document_path = save_upload(
            id_document, "verification", f"provider_{provider.id}_id"
        )
    if skill_proof is not None:
        provider.skill_proof_path = save_upload(
            skill_proof, "verification", f"provider_{provider.id}_skill"
        )

    db.add(current_user)
    db.add(provider)
    db.commit()
    db.refresh(provider)
    return provider


@router.patch("/me/location", response_model=MessageResponse)
def update_my_location(
    latitude: float = Query(...),
    longitude: float = Query(...),
    location_text: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    provider = db.query(Provider).filter(Provider.user_id == current_user.id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider profile not found.")
    provider.latitude = latitude
    provider.longitude = longitude
    if location_text:
        provider.location = location_text
    db.commit()
    return {"message": "Location updated successfully.", "success": True}


@router.get("/admin/all", response_model=List[ProviderOut])
def admin_get_all_providers(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return db.query(Provider).order_by(Provider.created_at.desc()).all()


@router.get("/", response_model=List[ProviderOut])
def get_providers(
    category_id: Optional[int] = Query(None),
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    db: Session = Depends(get_db),
):
    query = _approved_provider_query(db)
    if category_id:
        query = query.filter(Provider.category_id == category_id)
    results = query.all()
    return _sort_by_distance(results, user_lat, user_lon)


@router.get("/{provider_id}", response_model=ProviderOut)
def get_provider_by_id(
    provider_id: int,
    db: Session = Depends(get_db),
):
    provider = (
        db.query(Provider)
        .filter(Provider.id == provider_id, Provider.status == ProviderStatus.approved)
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    return provider


@router.patch("/{provider_id}/status", response_model=MessageResponse)
def update_provider_status(
    provider_id: int,
    data: ProviderStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    provider = db.query(Provider).filter(Provider.id == provider_id).first()
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found.")
    provider.status = ProviderStatus(data.status)
    db.commit()
    messages = {
        "approved": "Provider approved and is now visible to residents.",
        "rejected": "Provider registration rejected.",
        "suspended": "Provider suspended.",
        "pending": "Provider set back to pending.",
    }
    return {
        "message": messages.get(data.status, f"Status updated to {data.status}."),
        "success": True,
    }
