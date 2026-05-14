from datetime import datetime, timezone

from sqlmodel import Session
from src.modules.iam.infrastructure.models import UserModel
class IAMService:
    def __init__(self, session: Session):
        self.session = session

    async def register_user(self, user_data: dict):
        new_user = UserModel(
            email=user_data['email'],
            full_name=user_data['full_name'],
            hashed_password="hashed_content_here", 
            role=user_data.get('role', 'customer'),
            created_at=datetime.now(timezone.utc),
        )
        self.session.add(new_user)
        self.session.commit()
        self.session.refresh(new_user)
        return new_user
