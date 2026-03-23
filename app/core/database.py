# app/core/database.py
# Sets up the SQLite database connection using SQLAlchemy

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create the SQLite engine
# connect_args is needed for SQLite to allow multi-threaded access
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# SessionLocal is a factory for creating database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class that all database models will inherit from
Base = declarative_base()


def get_db():
    """
    Dependency function that provides a database session.
    Used in FastAPI route functions via Depends(get_db).
    Automatically closes the session when the request is done.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
