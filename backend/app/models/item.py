from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Integer, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    item_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    hsn_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"), nullable=False)
    last_purchase_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, code='{self.item_code}', name='{self.name}')>"
