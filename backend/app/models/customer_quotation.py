from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class CustomerQuotation(Base):
    __tablename__ = "customer_quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    quotation_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    comparison_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("quotation_comparisons.id"), nullable=False, index=True
    )
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=False, index=True
    )
    valid_till: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False, index=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    comparison: Mapped["QuotationComparison"] = relationship("QuotationComparison")
    customer: Mapped["Customer"] = relationship("Customer")
    supplier: Mapped["Supplier"] = relationship("Supplier")
    items: Mapped[List["CustomerQuotationItem"]] = relationship(
        "CustomerQuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="CustomerQuotationItem.id"
    )
    customer_orders: Mapped[List["CustomerOrder"]] = relationship(
        "CustomerOrder",
        back_populates="quotation"
    )

    def __repr__(self) -> str:
        return f"<CustomerQuotation(id={self.id}, no='{self.quotation_no}', status='{self.status}')>"


class CustomerQuotationItem(Base):
    __tablename__ = "customer_quotation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    quotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_quotations.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    supplier_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    customer_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1.00"), nullable=False)
    margin_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    quotation: Mapped["CustomerQuotation"] = relationship("CustomerQuotation", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<CustomerQuotationItem(id={self.id}, item_id={self.item_id}, price={self.customer_price})>"
