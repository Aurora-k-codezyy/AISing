from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_host: str = "xxxx"
    db_port: int = 3306
    db_name: str = "xxxx"
    db_user: str = "xxxx"
    db_password: str = "xxxx"
    data_dir: Path = Path("data")
    worker_enabled: bool = True
    database_url_override: str | None = None
    rvc_train_command: str = ""
    demucs_command: str = ""
    rvc_infer_command: str = ""
    rvc_model_filename: str = "model.pth"
    rvc_index_filename: str = "model.index"
    active_model_path: str = ""
    log_dir: Path = Path("logs")
    log_level: str = "INFO"
    admin_username: str = "admin"
    admin_password: str = "xxxx"
    oss_enabled: bool = False
    oss_endpoint: str = ""
    oss_internal_endpoint: str = ""
    oss_bucket: str = ""
    oss_access_key_id: str = ""
    oss_access_key_secret: str = ""
    oss_public_base_url: str = ""
    oss_key_prefix: str = "ai-sing"
    oss_upload_expire_seconds: int = 900

    model_config = SettingsConfigDict(env_prefix="AIS_", env_file=".env", extra="ignore")

    @property
    def database_url(self) -> str:
        if self.database_url_override:
            return self.database_url_override
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()

