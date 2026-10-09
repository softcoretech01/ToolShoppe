from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class QuotationComparison(Base):
    __tablename__ = "quotation_comparisons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    purchase_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("purchase_requests.id"), nullable=False, unique=True, index=True
    )
    recommended_supplier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    approved_supplier_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("suppliers.id"), nullable=True
    )
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False, index=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    purchase_request: Mapped["PurchaseRequest"] = relationship(
        "PurchaseRequest", back_populates="quotation_comparison"
    )
    recommended_supplier: Mapped[Optional["Supplier"]] = relationship(
        "Supplier", foreign_keys=[recommended_supplier_id]
    )
    approved_supplier: Mapped[Optional["Supplier"]] = relationship(
        "Supplier", foreign_keys=[approved_supplier_id]
    )

    def __repr__(self) -> str:
        return f"<QuotationComparison(id={self.id}, pr_id={self.purchase_request_id}, status='{self.status}')>"
