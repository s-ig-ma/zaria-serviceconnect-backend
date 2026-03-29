# app/routers/auth.py
# Handles user registration and login for all roles

import os
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.dependencies import get_current_user
from app.models.models import User, Provider, UserRole, Category
from app.schemas.schemas import ResidentRegister, LoginRequest, Token, UserOut, MessageResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


def validate_password_length(password: str):
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Password is too long for bcrypt ({len(password_bytes)} bytes received). "
                "Please use a shorter password."
            )
        )


@router.post("/register/resident", response_model=MessageResponse, status_code=201)
def register_resident(data: ResidentRegister, db: Session = Depends(get_db)):
    """Register a new resident account."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    validate_password_length(data.password)

    new_user = User(
        name=data.name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        location=data.location,
        role=UserRole.resident,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Resident account created successfully.", "success": True}


@router.post("/register/provider", response_model=MessageResponse, status_code=201)
async def register_provider(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    location: str = Form(None),
    category_id: int | None = Form(None),
    service_name: str | None = Form(None),
    years_of_experience: int = Form(0),
    description: str = Form(None),
    id_document: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Register a new service provider with ID document upload.
    Provider starts as 'pending' — admin approval required before appearing in search.
    """
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    validate_password_length(password)

    clean_service_name = service_name.strip() if service_name else None
    if category_id is None and not clean_service_name:
        raise HTTPException(
            status_code=400,
            detail="Please select a category or enter a custom service name."
        )

    if category_id is not None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Selected category was not found.")

    content = await id_document.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail="File must be smaller than 5 MB.")

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(id_document.filename)[1] if id_document.filename else ".pdf"
    safe_email = email.replace("@", "_at_").replace(".", "_")
    file_path = os.path.join(settings.UPLOAD_DIR, f"provider_{safe_email}{file_ext}")

    with open(file_path, "wb") as f:
        f.write(content)

    new_user = User(
        name=name, email=email, phone=phone,
        hashed_password=hash_password(password),
        location=location, role=UserRole.provider,
    )
    db.add(new_user)
    db.flush()

    new_provider = Provider(
        user_id=new_user.id,
        category_id=category_id,
        service_name=clean_service_name,
        years_of_experience=years_of_experience,
        description=description, id_document_path=file_path, location=location,
    )
    db.add(new_provider)
    db.commit()

    return {"message": "Provider account created. Awaiting admin approval.", "success": True}


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login for residents, providers, and admins. Returns a JWT token."""
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated.")

    token = create_access_token(data={"sub": user.email, "role": user.role.value, "user_id": user.id})

    return Token(access_token=token, token_type="bearer", role=user.role.value, user_id=user.id, name=user.name)


@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user
