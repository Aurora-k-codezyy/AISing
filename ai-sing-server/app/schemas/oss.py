from pydantic import BaseModel, Field


class PresignUploadRequest(BaseModel):
    category: str = Field(min_length=1, max_length=64)
    filename: str = Field(min_length=1, max_length=255)
    content_type: str = "application/octet-stream"


class PresignUploadResponse(BaseModel):
    object_key: str
    upload_url: str
    public_url: str
    headers: dict[str, str]
    expires_in: int


class UploadedObject(BaseModel):
    object_key: str = Field(min_length=1)
    public_url: str = Field(min_length=1)
    filename: str = ""
    content_type: str = "application/octet-stream"


class SongUploadCompleteRequest(BaseModel):
    task_name: str = ""
    audio: UploadedObject
    lyrics: UploadedObject
    processing_options: dict | None = None
    pitch_analysis: dict | None = None

