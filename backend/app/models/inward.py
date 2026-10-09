from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Inward(Base):
    __tablename__ = "inward"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    inward_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    grn_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grn.id"), nullable=False, unique=True, index=True
    )
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Pending", nullable=False, index=True)
    added_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    grn: Mapped["GRN"] = relationship("GRN", back_populates="inward")
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    items: Mapped[List["InwardItem"]] = relationship(
        "InwardItem",
        back_populates="inward",
        cascade="all, delete-orphan",
        order_by="InwardItem.id"
    )

    def __repr__(self) -> str:
        return f"<Inward(id={self.id}, no='{self.inward_no}', status='{self.status}')>"


class InwardItem(Base):
    __tablename__ = "inward_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    inward_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("inward.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    inward: Mapped["Inward"] = relationship("Inward", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<InwardItem(id={self.id}, item_id={self.item_id}, accepted_qty={self.accepted_qty})>"
