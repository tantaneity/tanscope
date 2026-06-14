from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class EventKind(StrEnum):
    IMAGE_SEARCH = "image_search"
    DOWNLOAD = "download"


class Base(DeclarativeBase):
    pass


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, index=True)
    kind: Mapped[str] = mapped_column(String(16), index=True)
    target: Mapped[str] = mapped_column(String(512))
    platform: Mapped[str | None] = mapped_column(String(32), index=True)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class TrackedAccount(Base):
    __tablename__ = "tracked_accounts"
    __table_args__ = (
        UniqueConstraint("chat_id", "platform", "username", name="uq_tracked_account"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, index=True)
    platform: Mapped[str] = mapped_column(String(32), index=True)
    username: Mapped[str] = mapped_column(String(128), index=True)
    primed: Mapped[bool] = mapped_column(Boolean, default=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
