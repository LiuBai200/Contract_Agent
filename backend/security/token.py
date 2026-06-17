import base64
import hashlib
import hmac
import json
import time
from typing import Any

from backend.config import settings


def create_access_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": int(time.time()) + settings.access_token_expire_minutes * 60,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_part = _b64encode(payload_bytes)
    signature = _sign(payload_part)
    return f"{payload_part}.{signature}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        payload_part, signature = token.split(".", 1)
    except ValueError:
        return None
    if not hmac.compare_digest(_sign(payload_part), signature):
        return None
    try:
        payload = json.loads(_b64decode(payload_part))
    except (ValueError, json.JSONDecodeError):
        return None
    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return payload


def _sign(payload_part: str) -> str:
    digest = hmac.new(settings.secret_key.encode("utf-8"), payload_part.encode("utf-8"), hashlib.sha256).digest()
    return _b64encode(digest)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
