# app/core/dependencies.py
# Reusable FastAPI dependencies for authentication and authorization

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.models import User, UserRole

# This tells FastAPI to look for a Bearer token in the Authorization header
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Extract and validate the JWT token from the request header.
    Returns the current logged-in user.
    Raises 401 if token is missing, invalid, or expired.
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = payload.get("sub")
    if email is None:
        raise HTTPException(status_code=401, detail="Token payload is malformed.")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    return user


def get_current_resident(current_user: User = Depends(get_current_user)) -> User:
    """Only allow residents to access this route."""
    if current_user.role != UserRole.resident:
        raise HTTPException(status_code=403, detail="Only residents can perform this action.")
    return current_user


def get_current_provider(current_user: User = Depends(get_current_user)) -> User:
    """Only allow providers to access this route."""
    if current_user.role != UserRole.provider:
        raise HTTPException(status_code=403, detail="Only providers can perform this action.")
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Only allow admins to access this route."""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Only admins can perform this action.")
    return current_user
