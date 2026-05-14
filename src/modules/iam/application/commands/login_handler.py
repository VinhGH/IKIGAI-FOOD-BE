from __future__ import annotations

from dataclasses import dataclass

from src.modules.iam.application.dtos import LoginRequest, LoginResponse
from src.modules.iam.domain.exceptions import (
    InvalidCredentialsException,
    UserNotActiveException,
)
from src.modules.iam.domain.ports import (
    PasswordHasherPort,
    RefreshTokenRepository,
    TokenServicePort,
    UserRepository,
)
from src.modules.iam.application.commands._token_utils import (
    ensure_refresh_payload,
    expires_at_from_payload,
)


@dataclass
class LoginHandler:
    user_repo: UserRepository
    password_hasher: PasswordHasherPort
    token_service: TokenServicePort
    refresh_token_repo: RefreshTokenRepository | None = None

    async def handle(self, request: LoginRequest) -> LoginResponse:
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise InvalidCredentialsException()

        if not self.password_hasher.verify(request.password, user.hashed_password.value):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise UserNotActiveException()

        if user.id is None:
            raise RuntimeError("User id is required for login")

        access_token = self.token_service.create_access_token(user.id, user.role.value)
        refresh_token = self.token_service.create_refresh_token(user.id)
        refresh_payload = ensure_refresh_payload(self.token_service, refresh_token)

        if self.refresh_token_repo is not None:
            await self.refresh_token_repo.create(
                token=refresh_token,
                user_id=user.id,
                expires_at=expires_at_from_payload(refresh_payload),
            )

        return LoginResponse.from_domain(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user,
        )
