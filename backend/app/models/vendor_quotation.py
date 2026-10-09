from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import String, DateTime, Date, Integer, Numeric, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class VendorQuotation(Base):
    __tablename__ = "vendor_quotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    quotation_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    purchase_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    quote_reference: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    quote_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    validity: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    delivery_days: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    freight: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Received", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="vendor_quotations"
    )
    supplier: Mapped["Supplier"] = relationship("Supplier")
    items: Mapped[List["QuotationItem"]] = relationship(
        "QuotationItem",
        back_populates="quotation",
        cascade="all, delete-orphan",
        order_by="QuotationItem.id"
    )

    def __repr__(self) -> str:
        return f"<VendorQuotation(id={self.id}, no='{self.quotation_no}', total={self.grand_total})>"


class QuotationItem(Base):
    __tablename__ = "quotation_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    quotation_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vendor_quotations.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(Integer, ForeignKey("items.id"), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    not_quoted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    quotation: Mapped["VendorQuotation"] = relationship("VendorQuotation", back_populates="items")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<QuotationItem(id={self.id}, item_id={self.item_id}, rate={self.rate}, not_quoted={self.not_quoted})>"
