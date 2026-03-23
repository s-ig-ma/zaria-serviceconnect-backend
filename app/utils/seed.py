# app/utils/seed.py
# Seeds the database with initial data: admin account and service categories.
# Run this once after the first database creation.

from sqlalchemy.orm import Session
from app.models.models import User, Category, UserRole
from app.core.security import hash_password


def seed_categories(db: Session):
    """Insert the 5 initial service categories if they don't exist."""
    categories = [
        {"name": "Plumbing", "description": "Pipe installation, leak repairs, and water systems", "icon": "plumbing"},
        {"name": "Electrical", "description": "Wiring, fixtures, and electrical repairs", "icon": "electrical"},
        {"name": "Cleaning", "description": "Home and office cleaning services", "icon": "cleaning"},
        {"name": "Appliance Repair", "description": "Repair of fridges, washing machines, ACs, and more", "icon": "appliance"},
        {"name": "Carpentry", "description": "Furniture making, repairs, and woodwork", "icon": "carpentry"},
    ]

    for cat_data in categories:
        existing = db.query(Category).filter(Category.name == cat_data["name"]).first()
        if not existing:
            db.add(Category(**cat_data))

    db.commit()
    print("✅ Categories seeded.")


def seed_admin(db: Session):
    """Create a default admin account if none exists."""
    admin_email = "admin@zariaserviceconnect.com"
    existing = db.query(User).filter(User.email == admin_email).first()

    if not existing:
        admin = User(
            name="System Admin",
            email=admin_email,
            phone="+2348000000000",
            hashed_password=hash_password("admin123"),  # Change in production!
            location="Zaria, Kaduna State",
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin account created: {admin_email} / admin123")
    else:
        print("ℹ️  Admin already exists.")


def run_seed(db: Session):
    """Run all seed functions."""
    seed_categories(db)
    seed_admin(db)
