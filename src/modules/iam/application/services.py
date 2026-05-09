from sqlmodel import Session, select
from src.modules.iam.infrastructure.models import UserModel
# Giả sử bạn có thư viện hash mật khẩu ở building_blocks
# from src.building_blocks.application.security import hash_password 

class IAMService:
    def __init__(self, session: Session):
        self.session = session

    async def register_user(self, user_data: dict):
        # 1. Logic kiểm tra email tồn tại...
        # 2. Hash mật khẩu
        new_user = UserModel(
            email=user_data['email'],
            full_name=user_data['full_name'],
            hashed_password="hashed_content_here", # Cần hash thật nhé
            role=user_data.get('role', 'customer')
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user