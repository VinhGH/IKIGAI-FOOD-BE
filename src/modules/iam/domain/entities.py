from datetime import datetime, timezone
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from src.modules.iam.domain.enum import UserRole, VerificationCodeType






class Address(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    
    address_name: Optional[str] = Field(default="Địa chỉ mặc định", description="Ví dụ: Nhà riêng, Văn phòng")
    is_default: bool = Field(default=False)
    
    
    province_code: int = Field(foreign_key="province.code")
    district_code: int = Field(foreign_key="district.code")
    ward_code: int = Field(foreign_key="ward.code")
    address_detail: str = Field(description="Số nhà, tên đường...")

    user: "User" = Relationship(back_populates="addresses")



class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = Field(default=None, unique=True)
    full_name: str
    role: UserRole = Field(default=UserRole.end_user)
    is_active: bool = Field(default=False)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    addresses: List[Address] = Relationship(back_populates="user")
    refresh_tokens: List["RefreshToken"] = Relationship(back_populates="user")
    codes: List["VerificationCode"] = Relationship(back_populates="user")



class RefreshToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True)
    user_id: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime
    is_revoked: bool = Field(default=False)
    user: User = Relationship(back_populates="refresh_tokens")

class VerificationCode(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    code: str
    expires_at: datetime
    code_type: VerificationCodeType
    user: User = Relationship(back_populates="codes")