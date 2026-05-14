from __future__ import annotations

from dataclasses import dataclass

from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.dtos import ResetPasswordRequest
from src.modules.iam.domain.exceptions import UserNotFoundException
from src.modules.iam.domain.ports import PasswordHasherPort, UserRepository
from src.modules.iam.domain.value_objects import HashedPassword


@dataclass
class ResetPasswordHandler:
    user_repo: UserRepository
    password_hasher: PasswordHasherPort
    event_bus: EventBus

    async def handle(self, request: ResetPasswordRequest) -> dict[str, str]:
        user = await self.user_repo.get_by_email(request.email)
        if user is None:
            raise UserNotFoundException(request.email)

        new_hashed_password = HashedPassword(self.password_hasher.hash(request.new_password))
        user.change_password(new_hashed_password, request.code)

        await self.user_repo.save(user)

        for event in user.pull_events():
            await self.event_bus.publish(event)

        return {"message": "Đặt lại mật khẩu thành công. Vui lòng đăng nhập lại."}
