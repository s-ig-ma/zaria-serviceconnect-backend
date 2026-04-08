# app/routers/auth.py
# Handles user registration and login for all roles

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import Category, Provider, User, UserRole
from app.schemas.schemas import LoginRequest, MessageResponse, ResidentRegister, Token, UserOut
from app.utils.uploads import save_upload

router = APIRouter(prefix="/auth", tags=["Authentication"])


def validate_password_length(password: str):
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Password is too long for bcrypt ({len(password_bytes)} bytes received). "
                "Please use a shorter password."
            ),
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
        home_address=data.home_address or data.location,
        role=UserRole.resident,
    )
    db.add(new_user)
    db.commit()
    return {"message": "Resident account created successfully.", "success": True}


@router.post("/register/provider", response_model=MessageResponse, status_code=201)
def register_provider(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    location: str | None = Form(None),
    category_id: int | None = Form(None),
    service_name: str | None = Form(None),
    years_of_experience: int = Form(0),
    description: str | None = Form(None),
    has_shop_in_zaria: bool = Form(False),
    shop_address: str | None = Form(None),
    passport_photo: UploadFile = File(...),
    id_document: UploadFile = File(...),
    skill_proof: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Register a new service provider with practical verification uploads."""
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered.")

    validate_password_length(password)

    clean_service_name = service_name.strip() if service_name else None
    if category_id is None and not clean_service_name:
        raise HTTPException(
            status_code=400,
            detail="Please select a category or enter a custom service name.",
        )

    if category_id is not None:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=400, detail="Selected category was not found.")

    clean_shop_address = shop_address.strip() if shop_address else None
    if has_shop_in_zaria and not clean_shop_address:
        raise HTTPException(status_code=400, detail="Please enter the shop address in Zaria.")

    safe_email = email.replace("@", "_at_").replace(".", "_")
    passport_photo_path = save_upload(passport_photo, "verification", f"{safe_email}_passport")
    id_document_path = save_upload(id_document, "verification", f"{safe_email}_id")
    skill_proof_path = save_upload(skill_proof, "verification", f"{safe_email}_skill")

    new_user = User(
        name=name,
        email=email,
        phone=phone,
        hashed_password=hash_password(password),
        location=location,
        role=UserRole.provider,
    )
    db.add(new_user)
    db.flush()

    new_provider = Provider(
        user_id=new_user.id,
        category_id=category_id,
        service_name=clean_service_name,
        years_of_experience=years_of_experience,
        description=description,
        passport_photo_path=passport_photo_path,
        id_document_path=id_document_path,
        skill_proof_path=skill_proof_path,
        has_shop_in_zaria=has_shop_in_zaria,
        shop_address=clean_shop_address,
        location=location,
    )
    db.add(new_provider)
    db.commit()

    return {"message": "Provider account created. Awaiting admin approval.", "success": True}


@router.post("/login", response_model=Token)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Login for residents, providers, and admins. Returns a JWT token."""
    user = db.query(User).filter(User.email == data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account has been deactivated.")

    token = create_access_token(data={"sub": user.email, "role": user.role.value, "user_id": user.id})

    return Token(
        access_token=token,
        token_type="bearer",
        role=user.role.value,
        user_id=user.id,
        name=user.name,
    )


@router.get("/me", response_model=UserOut)
def get_my_profile(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return current_user
