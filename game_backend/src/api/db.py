"""
Database session and engine management for the 3D adventure game backend using SQLAlchemy and SQLite.

Provides SessionLocal for DB operations and get_db dependency for FastAPI integration.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use SQLite (file-based) database by default.
DB_FILE = os.environ.get("GAME_DB_FILE", "game_backend.sqlite3")
DB_URL = f"sqlite:///{DB_FILE}"

engine = create_engine(
    DB_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# PUBLIC_INTERFACE
def get_db():
    """
    Dependency to provide a SQLAlchemy DB session for FastAPI route.
    Yields a session and ensures closure after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
