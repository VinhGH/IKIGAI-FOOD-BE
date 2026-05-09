from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel

class UserBase(SQLModel):
    email: str
    phone: Optional[str] = None
    full_name: str
    role: str = "customer" 
    is_active: bool = True

class User(UserBase):
    id: Optional[int] = None
    created_at: datetime = datetime.now()