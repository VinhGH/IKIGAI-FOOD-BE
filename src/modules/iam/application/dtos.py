from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.modules.iam.domain.entities import Address, User
from src.modules.iam.domain.value_objects import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

    @classmethod
    def from_domain(cls, user: User) -> "UserResponse":
        if user.id is None:
            raise RuntimeError("User id is required for response mapping")

        return cls(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name.value,
            role=user.role.value,
            is_active=user.is_active,
        )


class RegisterRequest(BaseModel):
    email: str
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8)
    role: UserRole = Field(default=UserRole.customer)
    phone: str | None = None


class VerifyEmailRequest(BaseModel):
    email: str
    code: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

    @classmethod
    def from_domain(
        cls,
        *,
        access_token: str,
        refresh_token: str,
        user: User,
    ) -> "LoginResponse":
        return cls(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse.from_domain(user),
        )


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    email: str
    code: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=8)


class AddressRequest(BaseModel):
    address_name: str = Field(default="Địa chỉ mặc định")
    is_default: bool = Field(default=False)
    province_code: int
    district_code: int
    ward_code: int
    address_detail: str


class AddressResponse(BaseModel):
    id: int
    address_name: str
    is_default: bool
    province_code: int
    district_code: int
    ward_code: int
    address_detail: str
    full_address: str

    @classmethod
    def from_domain(cls, address: Address, full_address: str) -> "AddressResponse":
        if address.id is None:
            raise RuntimeError("Address id is required for response mapping")

        return cls(
            id=address.id,
            address_name=address.address_name,
            is_default=address.is_default,
            province_code=address.province_code,
            district_code=address.district_code,
            ward_code=address.ward_code,
            address_detail=address.address_detail,
            full_address=full_address,
        )


class ProfileResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: int
    email: str
    full_name: str
    phone: str | None
    role: str
    is_active: bool
    created_at: datetime

    @classmethod
    def from_domain(cls, user: User) -> "ProfileResponse":
        if user.id is None:
            raise RuntimeError("User id is required for response mapping")

        return cls(
            id=user.id,
            email=user.email.value,
            full_name=user.full_name.value,
            phone=user.phone.value if user.phone else None,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        )
