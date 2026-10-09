from datetime import datetime
from decimal import Decimal
from sqlalchemy import DateTime, Numeric, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class RequestMargin(Base):
    __tablename__ = "request_margin"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), unique=True, nullable=False, index=True
    )
    purchase_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    sales_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    margin: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    margin_percent: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=Decimal("0.00"), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest", backref="margin_record")

    def __repr__(self) -> str:
        return f"<RequestMargin(cr_id={self.customer_request_id}, sales={self.sales_value}, margin={self.margin})>"
