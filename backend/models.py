"""SQLAlchemy models — compatible with PostgreSQL and SQLite."""
from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.types import TypeDecorator, CHAR
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import os
from database import Base


class GUID(TypeDecorator):
    """Database-agnostic UUID column.

    Stores as native UUID on PostgreSQL, as CHAR(36) on SQLite/other.
    Always presents as uuid.UUID in Python.
    """
    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))


# Use JSONB on PostgreSQL (indexed JSON), plain JSON elsewhere
_db_url = os.getenv("DATABASE_URL", "postgresql://")
if _db_url.startswith("postgresql"):
    from sqlalchemy.dialects.postgresql import JSONB as _JsonCol
else:
    _JsonCol = JSON


class User(Base):
    """User model."""
    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True)
    chess_com_username = Column(String(255), nullable=True)
    lichess_username = Column(String(255), nullable=True)
    chess_com_access_token = Column(Text, nullable=True)
    lichess_access_token = Column(Text, nullable=True)
    rating = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_sync = Column(DateTime, nullable=True)

    # Relationships
    patterns = relationship("Pattern", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="user", cascade="all, delete-orphan")


class Pattern(Base):
    """Pattern model."""
    __tablename__ = "patterns"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    pattern_type = Column(String(50), nullable=False)
    pattern_subtype = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  # Human-readable description
    severity = Column(Float, nullable=True)
    frequency = Column(Integer, default=0)
    first_seen = Column(DateTime, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    examples = Column(_JsonCol, nullable=True)
    pattern_metadata = Column(_JsonCol, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="patterns")
    progress = relationship("PatternProgress", back_populates="pattern", cascade="all, delete-orphan")


class PatternProgress(Base):
    """Pattern progress tracking model."""
    __tablename__ = "pattern_progress"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    pattern_id = Column(GUID(), ForeignKey("patterns.id", ondelete="CASCADE"))
    measured_at = Column(DateTime, default=datetime.utcnow)
    occurrence_rate = Column(Float, nullable=True)
    improvement_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    pattern = relationship("Pattern", back_populates="progress")


class UserSession(Base):
    """User session model."""
    __tablename__ = "user_sessions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"))
    token = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="sessions")


class Job(Base):
    """Background job tracking model."""
    __tablename__ = "jobs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Nullable for public analysis
    job_type = Column(String(50), nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)
    total_items = Column(Integer, nullable=True)
    processed_items = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    job_metadata = Column(_JsonCol, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")
