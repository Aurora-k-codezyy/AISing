from dataclasses import dataclass
from pathlib import Path
import os
import sys
from urllib.parse import urlparse
import requests

from aising_client.logging_config import app_data_dir

APP_NAME = "青玄"
APP_DISPLAY_NAME = "青玄"



def resource_path(relative_path: str) -> Path:
    if getattr(sys, "_MEIPASS", None):
        base_path = Path(sys._MEIPASS) / "aising_client"
    else:
        base_path = Path(__file__).resolve().parent
    return base_path / relative_path


APP_ICON_PATH = resource_path("resources/miaochang.png")
APP_ICON_ICO_PATH = resource_path("resources/miaochang.ico")
DELETE_ICON_PATH = resource_path("resources/delete.png")


@dataclass
class BrandingConfig:
    app_name: str
    display_name: str
    logo_path: Path
    icon_path: Path


DEFAULT_BRANDING = BrandingConfig(
    app_name=APP_NAME,
    display_name=APP_DISPLAY_NAME,
    logo_path=APP_ICON_PATH,
    icon_path=APP_ICON_PATH,
)


def _cache_asset(url: str, directory: Path, name: str) -> Path | None:
    if not url.startswith(("http://", "https://")):
        return None
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix not in {".ico", ".webp", ".bmp", ".png", ".jpeg", ".jpg"}:
        suffix = ".png"
    target = directory / f"{name}{suffix}"
    temporary = target.with_name(f".{target.name}.download")
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        if not response.content:
            return None
        directory.mkdir(parents=True, exist_ok=True)
        temporary.write_bytes(response.content)
        os.replace(temporary, target)
        return target
    except Exception:
        return target if target.is_file() else None
    finally:
        if temporary.exists():
            temporary.unlink()


def resolve_branding(payload: dict, cache_dir: Path | None = None) -> BrandingConfig:
    values = payload if isinstance(payload, dict) else {}
    app_name = str(values.get("app_name") or APP_NAME).strip() or APP_NAME
    display_name = str(values.get("display_name") or APP_DISPLAY_NAME).strip() or APP_DISPLAY_NAME
    directory = cache_dir or (app_data_dir() / "branding")
    logo = _cache_asset(str(values.get("logo_url") or ""), directory, "logo") or APP_ICON_PATH
    icon = _cache_asset(str(values.get("icon_url") or ""), directory, "icon") or logo or APP_ICON_PATH
    return BrandingConfig(
        app_name=app_name,
        display_name=display_name,
        logo_path=logo,
        icon_path=icon,
    )


def fetch_branding(api) -> BrandingConfig:
    try:
        if hasattr(api, "public_client_branding"):
            return resolve_branding(api.public_client_branding())
        return DEFAULT_BRANDING
    except Exception:
        return DEFAULT_BRANDING

