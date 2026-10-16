from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text

from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base

def utc_now() -> datetime:

    return datetime.now().replace(microsecond=0)

JOB_TYPE_VOICE_TRAIN = "voice_train"

JOB_TYPE_SONG_PROCESS = "song_process"

JOB_STATUS_QUEUED = "queued"

JOB_STATUS_RUNNING = "running"

JOB_STATUS_SUCCESS = "success"

JOB_STATUS_FAILED = "failed"

class Job(Base):

    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)

    type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)

    status: Mapped[str] = mapped_column(String(32), default=JOB_STATUS_QUEUED, nullable=False, index=True)

    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    input_path: Mapped[str] = mapped_column(Text, nullable=False)

    output_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)

    updated_at: Mapped[datetime] = mapped_column(

        DateTime,

        default=utc_now,

        onupdate=utc_now,

        nullable=False,

    )

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)

    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

