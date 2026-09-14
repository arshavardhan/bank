"""Database engine and session management."""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.config.settings import settings
from app.database.models import Base

# Determine connect args (e.g. check_same_thread for sqlite)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.DEBUG
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Create database tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency for database session."""
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
