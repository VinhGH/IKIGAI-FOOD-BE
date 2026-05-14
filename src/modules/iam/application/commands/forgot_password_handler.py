from __future__ import annotations

from dataclasses import dataclass

from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.dtos import ForgotPasswordRequest
from src.modules.iam.domain.ports import UserRepository


@dataclass
class ForgotPasswordHandler:
    user_repo: UserRepository
    event_bus: EventBus

    async def handle(self, request: ForgotPasswordRequest) -> dict[str, str]:
        user = await self.user_repo.get_by_email(request.email)
        if user is not None:
            user.request_password_reset()
            await self.user_repo.save(user)

            for event in user.pull_events():
                await self.event_bus.publish(event)

        return {"message": "Nếu email tồn tại, chúng tôi đã gửi mã OTP."}
