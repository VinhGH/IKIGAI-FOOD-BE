from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

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
from src.modules.iam.application.dtos import (
    AddressRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from src.modules.iam.application.queries.get_profile_query import GetProfileQuery
from src.modules.iam.application.queries.list_addresses_query import ListAddressesQuery
from src.modules.iam.domain.entities import User
from src.modules.iam.presentation.dependencies import (
    get_add_address_handler,
    get_change_password_handler,
    get_current_user,
    get_delete_address_handler,
    get_forgot_password_handler,
    get_get_profile_query,
    get_list_addresses_query,
    get_login_handler,
    get_logout_handler,
    get_refresh_token_handler,
    get_register_handler,
    get_reset_password_handler,
    get_set_default_address_handler,
    get_verify_email_handler,
    require_customer,
)

router = APIRouter(prefix="/v1", tags=["IAM"])


def _user_id(current_user: User) -> int:
    if current_user.id is None:
        raise RuntimeError("Current user id is required")
    return current_user.id


def _success(data: Any, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": jsonable_encoder(data)},
    )


@router.post("/auth/register", status_code=201)
async def register(
    request: RegisterRequest,
    handler: RegisterHandler = Depends(get_register_handler),
):
    result = await handler.handle(request)
    return _success(result, status_code=201)


@router.post("/auth/verify-email")
async def verify_email(
    request: VerifyEmailRequest,
    handler: VerifyEmailHandler = Depends(get_verify_email_handler),
):
    result = await handler.handle(request)
    return _success(result)


@router.post("/auth/login")
async def login(
    request: LoginRequest,
    handler: LoginHandler = Depends(get_login_handler),
):
    result = await handler.handle(request)
    return _success(result)


@router.post("/auth/refresh")
async def refresh(
    request: RefreshRequest,
    handler: RefreshTokenHandler = Depends(get_refresh_token_handler),
):
    result = await handler.handle(request)
    return _success(result)


@router.post("/auth/logout")
async def logout(
    request: RefreshRequest,
    current_user: User = Depends(get_current_user),
    handler: LogoutHandler = Depends(get_logout_handler),
):
    _ = current_user
    result = await handler.handle(request)
    return _success(result)


@router.post("/auth/forgot-password")
async def forgot_password(
    request: ForgotPasswordRequest,
    handler: ForgotPasswordHandler = Depends(get_forgot_password_handler),
):
    result = await handler.handle(request)
    return _success(result)


@router.post("/auth/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    handler: ResetPasswordHandler = Depends(get_reset_password_handler),
):
    result = await handler.handle(request)
    return _success(result)


@router.put("/auth/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    handler: ChangePasswordHandler = Depends(get_change_password_handler),
):
    result = await handler.handle(request, _user_id(current_user))
    return _success(result)


@router.get("/users/me")
async def get_profile(
    current_user: User = Depends(get_current_user),
    query: GetProfileQuery = Depends(get_get_profile_query),
):
    result = await query.handle(_user_id(current_user))
    return _success(result)


@router.get("/users/me/addresses")
async def list_addresses(
    current_user: User = Depends(require_customer),
    query: ListAddressesQuery = Depends(get_list_addresses_query),
):
    result = await query.handle(_user_id(current_user))
    return _success(result)


@router.post("/users/me/addresses", status_code=201)
async def add_address(
    request: AddressRequest,
    current_user: User = Depends(require_customer),
    handler: AddAddressHandler = Depends(get_add_address_handler),
):
    result = await handler.handle(request, _user_id(current_user))
    return _success(result, status_code=201)


@router.patch("/users/me/addresses/{address_id}/default")
async def set_default_address(
    address_id: int,
    current_user: User = Depends(require_customer),
    handler: SetDefaultAddressHandler = Depends(get_set_default_address_handler),
):
    result = await handler.handle(_user_id(current_user), address_id)
    return _success(result)


@router.delete("/users/me/addresses/{address_id}")
async def delete_address(
    address_id: int,
    current_user: User = Depends(require_customer),
    handler: DeleteAddressHandler = Depends(get_delete_address_handler),
):
    result = await handler.handle(_user_id(current_user), address_id)
    return _success(result)
