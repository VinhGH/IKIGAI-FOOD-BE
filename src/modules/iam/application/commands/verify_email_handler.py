from __future__ import annotations

from dataclasses import dataclass

from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.dtos import VerifyEmailRequest
from src.modules.iam.domain.exceptions import UserNotFoundException
from src.modules.iam.domain.ports import UserRepository


@dataclass
class VerifyEmailHandler:
    user_repo: UserRepository
    event_bus: EventBus

    async def handle(self, request: VerifyEmailRequest) -> dict[str, str]:
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise UserNotFoundException(request.email)

        user.activate(request.code)

        await self.user_repo.save(user)

        for event in user.pull_events():
            await self.event_bus.publish(event)

        return {"message": "Xác thực email thành công. Bạn có thể đăng nhập."}
