from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class SalesInvoice(Base):
    __tablename__ = "sales_invoices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    outward_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("outwards.id"), unique=True, nullable=False, index=True
    )
    customer_order_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_orders.id"), nullable=False, index=True
    )
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_terms: Mapped[str] = mapped_column(String(100), default="30 Days", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Issued", nullable=False, index=True)
    remarks: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    outward: Mapped["Outward"] = relationship("Outward", backref="sales_invoice")
    customer_order: Mapped["CustomerOrder"] = relationship("CustomerOrder")
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    customer: Mapped["Customer"] = relationship("Customer")
    items: Mapped[List["SalesInvoiceItem"]] = relationship(
        "SalesInvoiceItem",
        back_populates="sales_invoice",
        cascade="all, delete-orphan",
        order_by="SalesInvoiceItem.id"
    )

    def __repr__(self) -> str:
        return f"<SalesInvoice(id={self.id}, invoice_no='{self.invoice_no}', outward_id={self.outward_id})>"


class SalesInvoiceItem(Base):
    __tablename__ = "sales_invoice_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    sales_invoice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sales_invoices.id"), nullable=False, index=True
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
    sales_invoice: Mapped["SalesInvoice"] = relationship("SalesInvoice", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<SalesInvoiceItem(id={self.id}, item_id={self.item_id}, qty={self.quantity}, total={self.line_total})>"
