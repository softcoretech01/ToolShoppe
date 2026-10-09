from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Integer, Text, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CustomerRequest(Base):
    __tablename__ = "customer_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(Integer, ForeignKey("customers.id"), nullable=False, index=True)
    required_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    customer_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Requested", nullable=False, index=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer")
    items: Mapped[List["CustomerRequestItem"]] = relationship(
        "CustomerRequestItem",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="CustomerRequestItem.id"
    )
    purchase_request: Mapped[Optional["PurchaseRequest"]] = relationship(
        "PurchaseRequest",
        back_populates="customer_request",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<CustomerRequest(id={self.id}, request_no='{self.request_no}', status='{self.status}')>"


class CustomerRequestItem(Base):
    __tablename__ = "customer_request_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(Integer, ForeignKey("customer_requests.id"), nullable=False, index=True)
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    request: Mapped["CustomerRequest"] = relationship("CustomerRequest", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<CustomerRequestItem(id={self.id}, item_id={self.item_id}, qty={self.quantity})>"
