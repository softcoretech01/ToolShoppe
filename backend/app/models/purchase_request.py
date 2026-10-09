from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class PurchaseRequest(Base):
    __tablename__ = "purchase_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    pr_no: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, unique=True, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="Open", nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest", back_populates="purchase_request")
    rfq_suppliers: Mapped[List["RFQSupplier"]] = relationship(
        "RFQSupplier",
        back_populates="purchase_request",
        cascade="all, delete-orphan"
    )
    vendor_quotations: Mapped[List["VendorQuotation"]] = relationship(
        "VendorQuotation",
        back_populates="purchase_request",
        cascade="all, delete-orphan",
        order_by="VendorQuotation.id"
    )
    quotation_comparison: Mapped[Optional["QuotationComparison"]] = relationship(
        "QuotationComparison",
        back_populates="purchase_request",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<PurchaseRequest(id={self.id}, pr_no='{self.pr_no}', status='{self.status}')>"


class RFQSupplier(Base):
    __tablename__ = "rfq_suppliers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_requests.id"), nullable=False, index=True
    )
    supplier_id: Mapped[int] = mapped_column(Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    purchase_request: Mapped["PurchaseRequest"] = relationship("PurchaseRequest", back_populates="rfq_suppliers")
    supplier: Mapped["Supplier"] = relationship("Supplier")

    def __repr__(self) -> str:
        return f"<RFQSupplier(pr_id={self.purchase_request_id}, supplier_id={self.supplier_id})>"
