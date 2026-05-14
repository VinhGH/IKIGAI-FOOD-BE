from __future__ import annotations

from dataclasses import dataclass

from src.modules.iam.domain.exceptions import (
    AddressNotFoundException,
    UserNotFoundException,
)
from src.modules.iam.domain.ports import UserRepository


@dataclass
class DeleteAddressHandler:
    user_repo: UserRepository

    async def handle(self, current_user_id: int, address_id: int) -> dict[str, str]:
        user = await self.user_repo.get_by_id(current_user_id)
        if not user:
            raise UserNotFoundException(str(current_user_id))

        if not any(address.id == address_id for address in user.addresses):
            raise AddressNotFoundException(address_id)

        user.addresses = [
            address for address in user.addresses if address.id != address_id
        ]
        await self.user_repo.save(user)
        return {"message": "Đã xoá địa chỉ"}
