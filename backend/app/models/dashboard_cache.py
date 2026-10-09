from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class DashboardCache(Base):
    __tablename__ = "dashboard_cache"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    kpi_name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    kpi_value: Mapped[str] = mapped_column(Text, nullable=False)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<DashboardCache(kpi='{self.kpi_name}', updated='{self.last_updated}')>"
