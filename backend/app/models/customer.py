from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Integer, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    contact_person: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gstin: Mapped[str | None] = mapped_column(String(50), nullable=True)
    billing_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    shipping_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_markup: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("10.00"), nullable=False)
    payment_terms: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<Customer(id={self.id}, code='{self.customer_code}', name='{self.name}')>"
