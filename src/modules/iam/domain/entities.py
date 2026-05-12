from src.modules.iam.domain.enum import UserRole
from src.modules.iam.domain.enum import VerificationCodeType
from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel



class UserBase(SQLModel):
    email: str
    phone: Optional[str] = None
    full_name: str
    role: UserRole = UserRole.end_user
    is_active: bool = False

class User(UserBase):
    id: Optional[int] = None
    created_at: datetime = datetime.now()


class RefreshToken(SQLModel):
    id: Optional[int] = None
    token: str
    user_id: int
    created_at: datetime = datetime.now()
    expires_at: datetime
    is_revoked: bool = False

class VerificationCode(SQLModel):
    id: Optional[int] = None
    user_id: int
    code: str
    expires_at: datetime
    code_type: VerificationCodeType
  