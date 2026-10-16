from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import logging
import secrets
import time
from urllib.parse import quote, urlparse

import requests

import shutil

from app.core.config import Settings, get_settings


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OssObject:
    object_key: str
    public_url: str


class OssStorageError(RuntimeError):
    pass


class OssStorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return bool(
            self.settings.oss_enabled
            and self.settings.oss_bucket
            and self.settings.oss_endpoint
            and self.settings.oss_access_key_id
            and self.settings.oss_access_key_secret
        )

    def presign_upload(
        self,
        category: str,
        filename: str,
        content_type: str,
        owner_id: int | str | None = None,
    ) -> dict:
        object_key = self.build_object_key(category, filename, owner_id)
        headers = {"Content-Type": content_type or "application/octet-stream"}
        if not self.enabled:
            base_url = "http://127.0.0.1:8200"
            return {
                "object_key": object_key,
                "upload_url": f"{base_url}/api/oss/local-upload?object_key={object_key}",
                "public_url": f"{base_url}/api/oss/local-files/{object_key}",
                "headers": headers,
                "expires_in": self.settings.oss_upload_expire_seconds,
            }
        self._require_enabled()
        upload_url = self._bucket(self.settings.oss_endpoint).sign_url(
            "PUT",
            object_key,
            self.settings.oss_upload_expire_seconds,
            headers=headers,
        )
        return {
            "object_key": object_key,
            "upload_url": upload_url,
            "public_url": self.public_url(object_key),
            "headers": headers,
            "expires_in": self.settings.oss_upload_expire_seconds,
        }

    def upload_file(self, path: str | Path, category: str, owner_id: int | str | None = None) -> OssObject:
        source = Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"OSS upload source missing: {source}")
        object_key = self.build_object_key(category, source.name, owner_id)
        if not self.enabled:
            target = Path(self.settings.data_dir) / "local_oss" / object_key
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            base_url = "http://127.0.0.1:8200"
            public_url = f"{base_url}/api/oss/local-files/{object_key}"
            logger.info("Saved local object object_key=%s path=%s", object_key, target)
            return OssObject(object_key=object_key, public_url=public_url)
        self._require_enabled()
        logger.info("Uploading file to OSS via public endpoint object_key=%s source=%s", object_key, source)
        self._bucket(self.settings.oss_endpoint).put_object_from_file(
            object_key,
            str(source),
        )
        logger.info("Uploaded file to OSS object_key=%s bytes=%s", object_key, source.stat().st_size)
        return OssObject(object_key=object_key, public_url=self.public_url(object_key))

    def download_to_file(self, object_key_or_url: str, target: str | Path) -> Path:
        target_path = Path(target)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if object_key_or_url.startswith(("http://", "https://")):
            logger.info("Downloading OSS object via public URL source=%s target=%s", object_key_or_url, target_path)
            response = requests.get(object_key_or_url, timeout=120)
            response.raise_for_status()
            target_path.write_bytes(response.content)
            logger.info("Downloaded OSS object via public URL target=%s bytes=%s", target_path, target_path.stat().st_size)
            return target_path
        local_candidate = Path(self.settings.data_dir) / "local_oss" / object_key_or_url
        if local_candidate.is_file():
            shutil.copy2(local_candidate, target_path)
            return target_path
        object_key = self.object_key_from_url(object_key_or_url)
        if self.enabled and object_key:
            logger.info("Downloading OSS object via bucket object_key=%s target=%s", object_key, target_path)
            self._bucket(self.settings.oss_endpoint).get_object_to_file(
                object_key,
                str(target_path),
            )
            logger.info("Downloaded OSS object via bucket target=%s bytes=%s", target_path, target_path.stat().st_size)
            return target_path
        local_cand2 = Path(self.settings.data_dir) / "local_oss" / object_key
        if local_cand2.is_file():
            shutil.copy2(local_cand2, target_path)
            return target_path
        response = requests.get(object_key_or_url, timeout=120)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return target_path

    def build_object_key(self, category: str, filename: str, owner_id: int | str | None = None) -> str:
        safe_category = self._safe_path_part(category)
        safe_name = Path(filename or "upload.bin").name

        # 5. If it's a localhost/internal URL, fetch it locally
        if object_key_or_url.startswith(("http://127.0.0.1", "http://localhost")):
            logger.info("Downloading object via local server URL source=%s target=%s", object_key_or_url, target_path)
            response = requests.get(object_key_or_url, timeout=30)
            response.raise_for_status()
            target_path.write_bytes(response.content)
            return target_path

        # 6. Never connect to legacy remote cloud servers
        legacy_remotes = ["154.8.173.242", "aliyuncs.com", "igiggle.cn"]
        if any(r in object_key_or_url for r in legacy_remotes):
            raise FileNotFoundError(
                f"Local file not found for legacy remote object: {object_key_or_url}. "
                "Remote connection blocked per project local-only policy."
            )

        # 7. Fallback for other URLs
        response = requests.get(object_key_or_url, timeout=30)
        response.raise_for_status()
        target_path.write_bytes(response.content)
        return target_path

    def build_object_key(self, category: str, filename: str, owner_id: int | str | None = None) -> str:
        safe_category = self._safe_path_part(category)
        suffix = Path(filename).suffix or ".bin"
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        timestamp = int(now.timestamp() * 1000)
        token = secrets.token_hex(6)
        owner = str(owner_id or "common")
        prefix = (getattr(self.settings, "oss_prefix", None) or "ai-sing").strip("/")
        return f"{prefix}/{safe_category}/{owner}/{date_path}/{timestamp}-{token}{suffix}"

    def _bucket(self, endpoint: str):
        try:
            import oss2
            auth = oss2.Auth(self.settings.oss_access_key_id, self.settings.oss_access_key_secret)
            return oss2.Bucket(auth, endpoint, self.settings.oss_bucket)
        except ImportError:
            raise OssStorageError("oss2 package is not installed")

    def _require_enabled(self) -> None:
        if not self.enabled:
            raise OssStorageError("OSS is not configured. Please set AIS_OSS_* environment variables.")

    def _safe_path_part(self, value: str) -> str:
        cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.strip())
        return cleaned.strip("-") or "default"

