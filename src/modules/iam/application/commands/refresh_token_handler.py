from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from building_blocks.exceptions import AppException

from src.modules.iam.application.commands._token_utils import ensure_refresh_payload
from src.modules.iam.application.dtos import RefreshRequest
from src.modules.iam.domain.ports import (
    RefreshTokenRepository,
    TokenServicePort,
    UserRepository,
)


def _is_expired(expires_at: datetime) -> bool:
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc)


@dataclass
class RefreshTokenHandler:
    token_service: TokenServicePort
    refresh_token_repo: RefreshTokenRepository
    user_repo: UserRepository

    async def handle(self, request: RefreshRequest) -> dict[str, str]:
        refresh_payload = ensure_refresh_payload(self.token_service, request.refresh_token)

        token_record = await self.refresh_token_repo.get_by_token(request.refresh_token)
        if token_record is None:
            raise AppException(
                code="INVALID_TOKEN",
                message="Token không hợp lệ",
                status_code=401,
            )

        if token_record["is_revoked"]:
            raise AppException(
                code="TOKEN_REVOKED",
                message="Token đã bị thu hồi",
                status_code=401,
            )

        expires_at = token_record["expires_at"]
        if not isinstance(expires_at, datetime):
            raise AppException(
                code="INVALID_TOKEN",
                message="Token không hợp lệ",
                status_code=401,
            )

        if _is_expired(expires_at):
            raise AppException(
                code="TOKEN_EXPIRED",
                message="Token đã hết hạn",
                status_code=401,
            )

        user = await self.user_repo.get_by_id(token_record["user_id"])
        if user is None or user.id is None:
            raise AppException(
                code="INVALID_TOKEN",
                message="Token không hợp lệ",
                status_code=401,
            )

        if str(user.id) != str(refresh_payload.get("sub")):
            raise AppException(
                code="INVALID_TOKEN",
                message="Token không hợp lệ",
                status_code=401,
            )

        access_token = self.token_service.create_access_token(user.id, user.role.value)
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
