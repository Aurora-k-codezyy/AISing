from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.data_dir = Path(self.settings.data_dir)

    def ensure_dirs(self) -> None:
        for name in ("uploads", "outputs/models", "outputs/songs"):
            (self.data_dir / name).mkdir(parents=True, exist_ok=True)

    async def save_upload(self, upload: UploadFile, category: str) -> Path:
        self.ensure_dirs()
        suffix = Path(upload.filename or "upload.bin").suffix
        filename = f"{uuid4().hex}{suffix}"
        target = self.data_dir / "uploads" / category / filename
        target.parent.mkdir(parents=True, exist_ok=True)
        content = await upload.read()
        target.write_bytes(content)
        return target

    def model_output_dir(self, job_id: int) -> Path:
        path = self.data_dir / "outputs" / "models" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def song_output_dir(self, job_id: int) -> Path:
        path = self.data_dir / "outputs" / "songs" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def oss_cache_dir(self, job_id: int) -> Path:
        path = self.data_dir / "oss_cache" / str(job_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

