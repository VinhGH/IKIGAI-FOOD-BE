from sqlmodel import Field
from src.modules.iam.domain.entities import UserBase
from src.building_blocks.infrastructure.database import Base
from typing import Optional

# Đây mới là class tạo bảng trong DB
class UserModel(UserBase, table=True):
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str
