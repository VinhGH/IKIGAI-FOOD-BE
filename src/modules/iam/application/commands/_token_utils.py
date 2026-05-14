from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from building_blocks.exceptions import AppException


def ensure_refresh_payload(token_service, refresh_token: str) -> dict[str, Any]:
    payload = token_service.verify_access_token(refresh_token)
    if payload.get("type") != "refresh":
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        )
    return payload


def expires_at_from_payload(payload: dict[str, Any]) -> datetime:
    exp = payload.get("exp")
    if isinstance(exp, datetime):
        return exp.astimezone(timezone.utc)
    if isinstance(exp, (int, float)):
        return datetime.fromtimestamp(exp, tz=timezone.utc)

    raise AppException(
        code="INVALID_TOKEN",
        message="Token không hợp lệ",
        status_code=401,
    )
