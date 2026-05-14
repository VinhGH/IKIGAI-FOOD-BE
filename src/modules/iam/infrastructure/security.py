from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError

from building_blocks.exceptions import AppException
from src.modules.iam.domain.ports import PasswordHasherPort, TokenServicePort

ALGORITHM = "HS256"
DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS = 30


def _read_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise AppException(
            code="INVALID_SECURITY_CONFIG",
            message=f"Giá trị cấu hình {name} không hợp lệ",
            status_code=500,
        ) from exc


class BcryptPasswordHasher(PasswordHasherPort):
    def hash(self, plain_password: str) -> str:
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt())
        return hashed.decode("utf-8")

    def verify(self, plain_password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False


class JWTTokenService(TokenServicePort):
    def __init__(
        self,
        secret_key: str | None = None,
        access_token_expire_minutes: int | None = None,
        refresh_token_expire_days: int | None = None,
    ) -> None:
        self._secret_key = (secret_key or os.getenv("JWT_SECRET_KEY", "")).strip()
        if not self._secret_key:
            raise AppException(
                code="JWT_SECRET_KEY_MISSING",
                message="Thiếu JWT_SECRET_KEY trong môi trường",
                status_code=500,
            )

        self._access_token_expire_minutes = (
            access_token_expire_minutes
            if access_token_expire_minutes is not None
            else _read_int_env(
                "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
                DEFAULT_ACCESS_TOKEN_EXPIRE_MINUTES,
            )
        )
        self._refresh_token_expire_days = (
            refresh_token_expire_days
            if refresh_token_expire_days is not None
            else _read_int_env(
                "JWT_REFRESH_TOKEN_EXPIRE_DAYS",
                DEFAULT_REFRESH_TOKEN_EXPIRE_DAYS,
            )
        )

    def create_access_token(self, user_id: int, role: str) -> str:
        payload = self._base_payload(
            user_id=user_id,
            token_type="access",
            expires_delta=timedelta(minutes=self._access_token_expire_minutes),
        )
        payload["role"] = role
        return jwt.encode(payload, self._secret_key, algorithm=ALGORITHM)

    def create_refresh_token(self, user_id: int) -> str:
        payload = self._base_payload(
            user_id=user_id,
            token_type="refresh",
            expires_delta=timedelta(days=self._refresh_token_expire_days),
        )
        return jwt.encode(payload, self._secret_key, algorithm=ALGORITHM)

    def verify_access_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self._secret_key,
                algorithms=[ALGORITHM],
            )
        except ExpiredSignatureError as exc:
            raise AppException(
                code="TOKEN_EXPIRED",
                message="Token đã hết hạn",
                status_code=401,
            ) from exc
        except JWTError as exc:
            raise AppException(
                code="INVALID_TOKEN",
                message="Token không hợp lệ",
                status_code=401,
            ) from exc

    def _base_payload(
        self,
        user_id: int,
        token_type: str,
        expires_delta: timedelta,
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        return {
            "sub": str(user_id),
            "type": token_type,
            "exp": now + expires_delta,
        }
