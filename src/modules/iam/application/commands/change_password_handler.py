from __future__ import annotations

from dataclasses import dataclass

from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.dtos import ChangePasswordRequest
from src.modules.iam.domain.exceptions import (
    InvalidCredentialsException,
    UserNotFoundException,
)
from src.modules.iam.domain.ports import PasswordHasherPort, UserRepository
from src.modules.iam.domain.value_objects import HashedPassword


@dataclass
class ChangePasswordHandler:
    user_repo: UserRepository
    password_hasher: PasswordHasherPort
    event_bus: EventBus

    async def handle(
        self,
        request: ChangePasswordRequest,
        current_user_id: int,
    ) -> dict[str, str]:
        user = await self.user_repo.get_by_id(current_user_id)
        if user is None:
            raise UserNotFoundException(str(current_user_id))

        if not self.password_hasher.verify(
            request.current_password,
            user.hashed_password.value,
        ):
            raise InvalidCredentialsException()

        new_hashed_password = HashedPassword(self.password_hasher.hash(request.new_password))
        user.change_password(new_hashed_password)

        await self.user_repo.save(user)

        for event in user.pull_events():
            await self.event_bus.publish(event)

        return {"message": "Đổi mật khẩu thành công"}
