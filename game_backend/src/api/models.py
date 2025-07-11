"""
Database models for the 3D adventure game backend, using SQLAlchemy ORM.

This file defines User, Inventory, Progress, and Leaderboard models.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# PUBLIC_INTERFACE
class User(Base):
    """
    Represents a player/user in the game.
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(32), unique=True, nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    inventories = relationship("Inventory", back_populates="user", cascade="all, delete-orphan")
    progresses = relationship("Progress", back_populates="user", cascade="all, delete-orphan")
    leaderboard_entry = relationship("Leaderboard", uselist=False, back_populates="user", cascade="all, delete-orphan")

# PUBLIC_INTERFACE
class Inventory(Base):
    """
    Represents an item in a user's inventory.
    """
    __tablename__ = "inventories"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_name = Column(String(128), nullable=False)
    quantity = Column(Integer, default=1)

    user = relationship("User", back_populates="inventories")

    __table_args__ = (
        UniqueConstraint("user_id", "item_name", name="unique_inventory_item"),
    )

# PUBLIC_INTERFACE
class Progress(Base):
    """
    Tracks a user's in-game progress (e.g., level, checkpoint, score).
    """
    __tablename__ = "progresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    level = Column(Integer, default=1)
    checkpoint = Column(String(128))
    score = Column(Integer, default=0)
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="progresses")

    __table_args__ = (
        UniqueConstraint("user_id", "level", name="unique_progress_per_level"),
    )

# PUBLIC_INTERFACE
class Leaderboard(Base):
    """
    Represents a leaderboard entry (score/time/rank) for a user.
    """
    __tablename__ = "leaderboard"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    high_score = Column(Integer, default=0)
    best_time = Column(Integer, nullable=True)  # In seconds, optional
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="leaderboard_entry")
