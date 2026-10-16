from datetime import datetime
from typing import TypeVar
from pydantic import BaseModel


class JobResponse(BaseModel):
    id: int
    user_id: int | None
    type: str
    status: str
    progress: int
    input_path: str
    output_path: str | None
    metadata_json: str | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    is_cancellable: bool = False
    is_pausable: bool = False
    is_resumable: bool = False

    model_config = {"from_attributes": True}


T = TypeVar("T", bound=JobResponse)


def populate_job_flags(item: T) -> T:
    item.is_cancellable = item.status in ("queued", "running", "paused")
    item.is_pausable = item.status in ("queued", "running")
    item.is_resumable = item.status == "paused"
    return item


class AdminJobResponse(JobResponse):
    username: str | None = None
    phone: str | None = None
