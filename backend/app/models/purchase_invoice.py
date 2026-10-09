from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class PurchaseInvoice(Base):
    __tablename__ = "purchase_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    internal_invoice_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    grn_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("grn.id"), unique=True, nullable=False, index=True
    )
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    supplier_invoice_no: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    supplier_invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Recorded", nullable=False, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    supplier: Mapped["Supplier"] = relationship("Supplier")
    grn: Mapped["GRN"] = relationship("GRN", backref="purchase_invoice")
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    items: Mapped[List["PurchaseInvoiceItem"]] = relationship(
        "PurchaseInvoiceItem",
        back_populates="purchase_invoice",
        cascade="all, delete-orphan",
        order_by="PurchaseInvoiceItem.id"
    )

    def __repr__(self) -> str:
        return f"<PurchaseInvoice(id={self.id}, internal_no='{self.internal_invoice_no}', supplier_invoice='{self.supplier_invoice_no}')>"


class PurchaseInvoiceItem(Base):
    __tablename__ = "purchase_invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_invoices.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    unit: Mapped[str] = mapped_column(String(50), default="Nos", nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("18.00"), nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    purchase_invoice: Mapped["PurchaseInvoice"] = relationship("PurchaseInvoice", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<PurchaseInvoiceItem(id={self.id}, item_id={self.item_id}, qty={self.quantity}, total={self.line_total})>"
