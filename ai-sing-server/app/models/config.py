from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ProductConfig(Base):
    __tablename__ = "product_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    signup_bonus_credits: Mapped[int] = mapped_column(Integer, default=480, nullable=False)
    voice_train_cost: Mapped[int] = mapped_column(Integer, default=450, nullable=False)
    song_process_cost: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    recharge_price_per_credit: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    daily_free_credits: Mapped[int] = mapped_column(Integer, default=5, nullable=False)


class SupportInfo(Base):
    __tablename__ = "support_info"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    name: Mapped[str] = mapped_column(String(128), default="官方客服", nullable=False)
    qr_code_path: Mapped[str] = mapped_column(Text, default="", nullable=False)
