from __future__ import annotations

from dataclasses import dataclass

from building_blocks.exceptions import AppException

from src.modules.iam.application.commands._token_utils import ensure_refresh_payload
from src.modules.iam.application.dtos import RefreshRequest
from src.modules.iam.domain.ports import RefreshTokenRepository, TokenServicePort


@dataclass
class LogoutHandler:
    token_service: TokenServicePort
    refresh_token_repo: RefreshTokenRepository

    async def handle(self, request: RefreshRequest) -> dict[str, str]:
        try:
            ensure_refresh_payload(self.token_service, request.refresh_token)
        except AppException:
            return {"message": "Đăng xuất thành công"}

        await self.refresh_token_repo.revoke(request.refresh_token)
        return {"message": "Đăng xuất thành công"}
