from __future__ import annotations

from dataclasses import dataclass

from src.modules.iam.application.dtos import ProfileResponse
from src.modules.iam.domain.exceptions import UserNotFoundException
from src.modules.iam.domain.ports import UserRepository


@dataclass
class GetProfileQuery:
    user_repo: UserRepository

    async def handle(self, current_user_id: int) -> ProfileResponse:
        user = await self.user_repo.get_by_id(current_user_id)
        if not user:
            raise UserNotFoundException(str(current_user_id))

        return ProfileResponse.from_domain(user)
