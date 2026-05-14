from datetime import datetime
from typing import ClassVar, List, Optional

from sqlmodel import Field, Relationship, SQLModel


class UserModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "users"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    phone: Optional[str] = Field(default=None, unique=True, index=True)
    full_name: str
    hashed_password: str
    role: str
    is_active: bool = Field(default=False)
    created_at: datetime

    addresses: List["AddressModel"] = Relationship(back_populates="user")
    verification_codes: List["VerificationCodeModel"] = Relationship(back_populates="user")


class AddressModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "addresses"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    address_name: str = Field(default="Địa chỉ mặc định")
    is_default: bool = Field(default=False)
    province_code: int
    district_code: int
    ward_code: int
    address_detail: str

    user: "UserModel" = Relationship(back_populates="addresses")


class VerificationCodeModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "verification_codes"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    code: str
    code_type: str
    expires_at: datetime

    user: "UserModel" = Relationship(back_populates="verification_codes")


class RefreshTokenModel(SQLModel, table=True):
    __tablename__: ClassVar[str] = "refresh_tokens"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = Field(default=False)
