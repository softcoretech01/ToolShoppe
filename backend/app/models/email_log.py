from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, utc_now


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    document_type: Mapped[str] = mapped_column(String(50), default="RFQ", nullable=False, index=True)
    document_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Sent", nullable=False, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<EmailLog(id={self.id}, type='{self.document_type}', to='{self.recipient}', status='{self.status}')>"
