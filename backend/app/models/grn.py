from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class GRN(Base):
    __tablename__ = "grn"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    grn_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    purchase_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_orders.id"), nullable=False, index=True
    )
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    challan_no: Mapped[str] = mapped_column(String(100), nullable=False)
    supplier_invoice_ref: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    received_by: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Received", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    purchase_order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder")
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    supplier: Mapped["Supplier"] = relationship("Supplier")
    items: Mapped[List["GRNItem"]] = relationship(
        "GRNItem",
        back_populates="grn",
        cascade="all, delete-orphan",
        order_by="GRNItem.id"
    )
    inward: Mapped[Optional["Inward"]] = relationship(
        "Inward",
        back_populates="grn",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<GRN(id={self.id}, no='{self.grn_no}', po_id={self.purchase_order_id})>"


class GRNItem(Base):
    __tablename__ = "grn_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    grn_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grn.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    ordered_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    received_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    accepted_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    rejected_qty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    purchase_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    grn: Mapped["GRN"] = relationship("GRN", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<GRNItem(id={self.id}, item_id={self.item_id}, received={self.received_qty}, accepted={self.accepted_qty})>"
