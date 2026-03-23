# main.py
# ─────────────────────────────────────────────────────────────────────────────
# FastAPI application entry point.
# Run with: uvicorn main:app --reload --host 0.0.0.0
# ─────────────────────────────────────────────────────────────────────────────

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.models.models import Base
from app.utils.seed import run_seed

# Import all routers
from app.routers import auth, categories, providers, bookings, reviews, users
from app.routers import complaints   # ← NEW: complaint system

# Create all database tables (including the new complaints table)
Base.metadata.create_all(bind=engine)

# ── App setup ─────────────────────────────────────────────────────────────────
app = FastAPI(
    title    = settings.APP_NAME,
    version  = settings.APP_VERSION,
    docs_url = "/docs",
    redoc_url= "/redoc",
    description="""
## Zaria ServiceConnect API

### Authentication
Login at `/auth/login` to get a JWT token.
Include it in requests as: `Authorization: Bearer <token>`

### Roles
- **Resident**: browse providers, book services, submit complaints
- **Provider**: manage bookings
- **Admin**: approve providers, manage complaints
    """
)

# ── CORS (allows React dashboard and mobile app to connect) ───────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Serve uploaded documents as static files ──────────────────────────────────
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# ── Register all routers ──────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(categories.router)
app.include_router(providers.router)
app.include_router(bookings.router)
app.include_router(reviews.router)
app.include_router(complaints.router)   # ← NEW
app.include_router(users.router)


# ── On startup: create tables and seed initial data ───────────────────────────
@app.on_event("startup")
def startup_event():
    db = SessionLocal()
    try:
        run_seed(db)
    finally:
        db.close()


# ── Health check ──────────────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
def health_check():
    return {
        "status" : "running",
        "app"    : settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs"   : "/docs"
    }
