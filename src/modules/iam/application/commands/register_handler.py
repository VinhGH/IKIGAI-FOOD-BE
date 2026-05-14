from __future__ import annotations

from dataclasses import dataclass

from building_blocks.infrastructure.event_bus import EventBus

from src.modules.iam.application.dtos import RegisterRequest, UserResponse
from src.modules.iam.domain.entities import User
from src.modules.iam.domain.exceptions import (
    EmailAlreadyExistsException,
    PhoneAlreadyExistsException,
)
from src.modules.iam.domain.ports import PasswordHasherPort, UserRepository
from src.modules.iam.domain.value_objects import Email, FullName, HashedPassword, Phone


@dataclass
class RegisterHandler:
    user_repo: UserRepository
    password_hasher: PasswordHasherPort
    event_bus: EventBus

    async def handle(self, request: RegisterRequest) -> UserResponse:
        if await self.user_repo.exists_by_email(request.email):
            raise EmailAlreadyExistsException(request.email)

        if request.phone and await self.user_repo.exists_by_phone(request.phone):
            raise PhoneAlreadyExistsException(request.phone)

        user = User.register(
            email=Email(request.email),
            full_name=FullName(request.full_name),
            hashed_password=HashedPassword(self.password_hasher.hash(request.password)),
            role=request.role,
            phone=Phone(request.phone) if request.phone else None,
        )
        user.create_email_verification_code()

        saved_user = await self.user_repo.save(user)

        for event in user.pull_events():
            await self.event_bus.publish(event)

        return UserResponse.from_domain(saved_user)
