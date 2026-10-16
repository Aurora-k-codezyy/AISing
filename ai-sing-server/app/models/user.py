from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

def utc_now() -> datetime:

    return datetime.now().replace(microsecond=0)

class User(Base):

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    username: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)

    password_hash: Mapped[str] = mapped_column(String(256), default="", nullable=False)

    phone: Mapped[str] = mapped_column(String(32), default="", index=True, nullable=False)

    credits: Mapped[int] = mapped_column(Integer, default=480, nullable=False)

    active_token: Mapped[str | None] = mapped_column(String(128), default=None, unique=True, index=True, nullable=True)

    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

