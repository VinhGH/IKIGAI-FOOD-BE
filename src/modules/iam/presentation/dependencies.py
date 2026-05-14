from __future__ import annotations

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from building_blocks.exceptions import AppException
from building_blocks.infrastructure.database import get_session
from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.commands.add_address_handler import AddAddressHandler
from src.modules.iam.application.commands.change_password_handler import (
    ChangePasswordHandler,
)
from src.modules.iam.application.commands.delete_address_handler import (
    DeleteAddressHandler,
)
from src.modules.iam.application.commands.forgot_password_handler import (
    ForgotPasswordHandler,
)
from src.modules.iam.application.commands.login_handler import LoginHandler
from src.modules.iam.application.commands.logout_handler import LogoutHandler
from src.modules.iam.application.commands.refresh_token_handler import (
    RefreshTokenHandler,
)
from src.modules.iam.application.commands.register_handler import RegisterHandler
from src.modules.iam.application.commands.reset_password_handler import (
    ResetPasswordHandler,
)
from src.modules.iam.application.commands.set_default_address_handler import (
    SetDefaultAddressHandler,
)
from src.modules.iam.application.commands.verify_email_handler import (
    VerifyEmailHandler,
)
from src.modules.iam.application.queries.get_profile_query import GetProfileQuery
from src.modules.iam.application.queries.list_addresses_query import ListAddressesQuery
from src.modules.iam.domain.entities import User
from src.modules.iam.domain.ports import (
    AddressRepository,
    LocationPort,
    PasswordHasherPort,
    RefreshTokenRepository,
    TokenServicePort,
    UserRepository,
)
from src.modules.iam.infrastructure.repositories import (
    AddressRepositoryImpl,
    RefreshTokenRepositoryImpl,
    UserRepositoryImpl,
)
from src.modules.iam.infrastructure.security import (
    BcryptPasswordHasher,
    JWTTokenService,
)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)

_event_bus = EventBus()


class _StaticLocationPort(LocationPort):
    async def resolve_address(
        self,
        province_code: int,
        district_code: int,
        ward_code: int,
    ) -> str:
        return ""


async def get_event_bus() -> EventBus:
    return _event_bus


def get_password_hasher() -> PasswordHasherPort:
    return BcryptPasswordHasher()


def get_token_service() -> TokenServicePort:
    return JWTTokenService()


def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> UserRepository:
    return UserRepositoryImpl(session)


def get_address_repository(
    session: AsyncSession = Depends(get_session),
) -> AddressRepository:
    return AddressRepositoryImpl(session)


def get_refresh_token_repository(
    session: AsyncSession = Depends(get_session),
) -> RefreshTokenRepository:
    return RefreshTokenRepositoryImpl(session)


def get_location_port() -> LocationPort:
    return _StaticLocationPort()


def get_register_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    event_bus: EventBus = Depends(get_event_bus),
) -> RegisterHandler:
    return RegisterHandler(user_repo, password_hasher, event_bus)


def get_verify_email_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    event_bus: EventBus = Depends(get_event_bus),
) -> VerifyEmailHandler:
    return VerifyEmailHandler(user_repo, event_bus)


def get_login_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    token_service: TokenServicePort = Depends(get_token_service),
    refresh_token_repo: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
) -> LoginHandler:
    return LoginHandler(user_repo, password_hasher, token_service, refresh_token_repo)


def get_refresh_token_handler(
    token_service: TokenServicePort = Depends(get_token_service),
    refresh_token_repo: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
    user_repo: UserRepository = Depends(get_user_repository),
) -> RefreshTokenHandler:
    return RefreshTokenHandler(token_service, refresh_token_repo, user_repo)


def get_logout_handler(
    token_service: TokenServicePort = Depends(get_token_service),
    refresh_token_repo: RefreshTokenRepository = Depends(
        get_refresh_token_repository
    ),
) -> LogoutHandler:
    return LogoutHandler(token_service, refresh_token_repo)


def get_forgot_password_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    event_bus: EventBus = Depends(get_event_bus),
) -> ForgotPasswordHandler:
    return ForgotPasswordHandler(user_repo, event_bus)


def get_reset_password_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    event_bus: EventBus = Depends(get_event_bus),
) -> ResetPasswordHandler:
    return ResetPasswordHandler(user_repo, password_hasher, event_bus)


def get_change_password_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
    event_bus: EventBus = Depends(get_event_bus),
) -> ChangePasswordHandler:
    return ChangePasswordHandler(user_repo, password_hasher, event_bus)


def get_get_profile_query(
    user_repo: UserRepository = Depends(get_user_repository),
) -> GetProfileQuery:
    return GetProfileQuery(user_repo)


def get_list_addresses_query(
    address_repo: AddressRepository = Depends(get_address_repository),
    location_port: LocationPort = Depends(get_location_port),
) -> ListAddressesQuery:
    return ListAddressesQuery(address_repo, location_port)


def get_add_address_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    location_port: LocationPort = Depends(get_location_port),
) -> AddAddressHandler:
    return AddAddressHandler(user_repo, location_port)


def get_delete_address_handler(
    user_repo: UserRepository = Depends(get_user_repository),
) -> DeleteAddressHandler:
    return DeleteAddressHandler(user_repo)


def get_set_default_address_handler(
    user_repo: UserRepository = Depends(get_user_repository),
) -> SetDefaultAddressHandler:
    return SetDefaultAddressHandler(user_repo)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    user_repo: UserRepository = Depends(get_user_repository),
    token_service: TokenServicePort = Depends(get_token_service),
) -> User:
    if not token:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        )

    payload = token_service.verify_access_token(token)
    if payload.get("type") != "access":
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        )

    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub.strip():
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        )

    try:
        user_id = int(sub)
    except ValueError as exc:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        ) from exc

    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise AppException(
            code="INVALID_TOKEN",
            message="Token không hợp lệ",
            status_code=401,
        )

    return user


async def require_customer(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role.value != "customer":
        raise AppException(
            code="FORBIDDEN",
            message="Không có quyền truy cập",
            status_code=403,
        )
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role.value != "admin":
        raise AppException(
            code="FORBIDDEN",
            message="Không có quyền truy cập",
            status_code=403,
        )
    return current_user
