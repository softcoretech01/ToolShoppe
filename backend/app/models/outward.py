from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class Outward(Base):
    __tablename__ = "outwards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    outward_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_orders.id"), nullable=False, index=True
    )
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    dc_no: Mapped[str] = mapped_column(String(100), nullable=False)
    dispatch_date: Mapped[date] = mapped_column(Date, nullable=False)
    dispatch_mode: Mapped[str] = mapped_column(String(50), default="Road", nullable=False)
    vehicle_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Dispatched", nullable=False, index=True)
    total_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    customer_order: Mapped["CustomerOrder"] = relationship("CustomerOrder")
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    customer: Mapped["Customer"] = relationship("Customer")
    items: Mapped[List["OutwardItem"]] = relationship(
        "OutwardItem",
        back_populates="outward",
        cascade="all, delete-orphan",
        order_by="OutwardItem.id"
    )

    @property
    def dc_number(self) -> str:
        return self.dc_no

    @property
    def vehicle_or_courier(self) -> Optional[str]:
        return self.vehicle_no

    def __repr__(self) -> str:
        return f"<Outward(id={self.id}, no='{self.outward_no}', so_id={self.customer_order_id})>"


class OutwardItem(Base):
    __tablename__ = "outward_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    outward_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("outwards.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    available_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    dispatched_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="Nos", nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    outward: Mapped["Outward"] = relationship("Outward", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    @property
    def dispatch_qty(self) -> Decimal:
        return self.dispatched_qty

    @property
    def rate(self) -> Decimal:
        return self.unit_price

    def __repr__(self) -> str:
        return f"<OutwardItem(id={self.id}, item_id={self.item_id}, dispatched_qty={self.dispatched_qty})>"
