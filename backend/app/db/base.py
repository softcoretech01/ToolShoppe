from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 Base class for all database models."""
    pass


def utc_now() -> datetime:
    """Helper to return UTC timestamp."""
    return datetime.now(timezone.utc)
