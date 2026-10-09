from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Numeric, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, utc_now


class StockLedger(Base):
    __tablename__ = "stock_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    movement_type: Mapped[str] = mapped_column(String(50), default="IN", nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), default="GRN", nullable=False, index=True)
    reference_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<StockLedger(id={self.id}, cr_id={self.customer_request_id}, item_id={self.item_id}, type='{self.movement_type}', qty={self.quantity})>"


class StockSummary(Base):
    __tablename__ = "stock_summary"
    __table_args__ = (
        UniqueConstraint("customer_request_id", "item_id", name="uq_stock_summary_cr_item"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    customer_request_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customer_requests.id"), nullable=False, index=True
    )
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, index=True
    )
    qty_in: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    qty_out: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    on_hand: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    stock_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)

    # Relationships
    customer_request: Mapped["CustomerRequest"] = relationship("CustomerRequest")
    item: Mapped["Item"] = relationship("Item")

    def __repr__(self) -> str:
        return f"<StockSummary(id={self.id}, cr_id={self.customer_request_id}, item_id={self.item_id}, on_hand={self.on_hand})>"
