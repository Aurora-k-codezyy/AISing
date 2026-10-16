from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

def utc_now() -> datetime:

    return datetime.now().replace(microsecond=0)

CREDIT_TYPE_GRANT = "grant"

CREDIT_TYPE_RECHARGE = "recharge"

CREDIT_TYPE_CONSUME = "consume"

CREDIT_TYPE_ADJUST = "adjust"

class CreditTransaction(Base):

    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)

    type: Mapped[str] = mapped_column(String(32), index=True, nullable=False)

    amount: Mapped[int] = mapped_column(Integer, nullable=False)

    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)

    note: Mapped[str] = mapped_column(Text, default="", nullable=False)

    job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

