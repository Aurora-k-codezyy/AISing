from __future__ import annotations

import base64
from datetime import datetime
import os

EXPIRY_FIELD_NAME = "z9q"
EXPIRY_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_EXPIRY_CRYPTO_KEY = "qingxuan-expiry-2026"
LEGACY_EXPIRY_CRYPTO_KEY = "miaochang-expiry-2026"


def crypto_key() -> str:
    return os.getenv("AIS_EXPIRY_CRYPTO_KEY") or DEFAULT_EXPIRY_CRYPTO_KEY


def encrypt_expiry_token(value: str, key: str | None = None) -> str:
    secret = (key or crypto_key()).encode("utf-8")
    payload = value.encode("utf-8")
    encrypted = bytes(b ^ secret[i % len(secret)] for i, b in enumerate(payload))
    return base64.urlsafe_b64encode(encrypted).decode("ascii")


def decrypt_expiry_token(value: str, key: str | None = None) -> str:
    if not value:
        return "2099-12-31 23:59:59"
    keys_to_try = [key] if key else [
        crypto_key(),
        DEFAULT_EXPIRY_CRYPTO_KEY,
        LEGACY_EXPIRY_CRYPTO_KEY,
    ]
    for k in keys_to_try:
        try:
            secret = k.encode("utf-8")
            payload = base64.urlsafe_b64decode(value.encode("ascii"))
            decrypted = bytes(b ^ secret[i % len(secret)] for i, b in enumerate(payload)).decode("utf-8")
            # Strict verification: must match EXPIRY_FORMAT
            norm = decrypted.strip().replace("T", " ")[:19]
            datetime.strptime(norm, EXPIRY_FORMAT)
            return norm
        except Exception:
            continue
    return "2099-12-31 23:59:59"


def parse_beijing_expiry(value: str) -> datetime:
    try:
        normalized = value.strip().replace("T", " ")[:19]
        return datetime.strptime(normalized, EXPIRY_FORMAT)
    except Exception:
        return datetime(2099, 12, 31, 23, 59, 59)


def is_expired_beijing(value: str, now: datetime | None = None) -> bool:
    try:
        dt = parse_beijing_expiry(value)
        current = now or datetime.now()
        return dt <= current
    except Exception:
        return False

