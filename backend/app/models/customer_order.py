from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CustomerOrder(Base):
    __tablename__ = "customer_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    order_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    quotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_quotations.id"), nullable=False, index=True
    )
    customer_po_number: Mapped[str] = mapped_column(String(100), nullable=False)
    po_date: Mapped[date] = mapped_column(Date, nullable=False)
    delivery_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    quotation: Mapped["CustomerQuotation"] = relationship("CustomerQuotation", back_populates="customer_orders")
    items: Mapped[List["CustomerOrderItem"]] = relationship(
        "CustomerOrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        order_by="CustomerOrderItem.id"
    )
    purchase_orders: Mapped[List["PurchaseOrder"]] = relationship(
        "PurchaseOrder",
        back_populates="customer_order"
    )

    def __repr__(self) -> str:
        return f"<CustomerOrder(id={self.id}, no='{self.order_no}', po='{self.customer_po_number}')>"


class CustomerOrderItem(Base):
    __tablename__ = "customer_order_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_orders.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1.00"), nullable=False)
    selling_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    order: Mapped["CustomerOrder"] = relationship("CustomerOrder", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<CustomerOrderItem(id={self.id}, item_id={self.item_id}, qty={self.quantity})>"
