from __future__ import annotations

from dataclasses import dataclass

from src.modules.iam.application.dtos import AddressRequest, AddressResponse
from src.modules.iam.domain.entities import Address
from src.modules.iam.domain.exceptions import UserNotFoundException
from src.modules.iam.domain.ports import LocationPort, UserRepository


@dataclass
class AddAddressHandler:
    user_repo: UserRepository
    location_port: LocationPort

    async def handle(
        self,
        request: AddressRequest,
        current_user_id: int,
    ) -> AddressResponse:
        user = await self.user_repo.get_by_id(current_user_id)
        if not user:
            raise UserNotFoundException(str(current_user_id))

        address = Address(
            id=None,
            user_id=user.id,
            address_name=request.address_name,
            is_default=request.is_default,
            province_code=request.province_code,
            district_code=request.district_code,
            ward_code=request.ward_code,
            address_detail=request.address_detail,
        )
        user.add_address(address)

        saved_user = await self.user_repo.save(user)
        saved_address = self._find_saved_address(saved_user.addresses, address)
        location_address = await self.location_port.resolve_address(
            saved_address.province_code,
            saved_address.district_code,
            saved_address.ward_code,
        )
        full_address = ", ".join(
            part for part in (saved_address.address_detail, location_address) if part
        )
        return AddressResponse.from_domain(saved_address, full_address)

    @staticmethod
    def _find_saved_address(addresses: list[Address], target: Address) -> Address:
        matching = [
            address
            for address in addresses
            if address.address_name == target.address_name
            and address.is_default == target.is_default
            and address.province_code == target.province_code
            and address.district_code == target.district_code
            and address.ward_code == target.ward_code
            and address.address_detail == target.address_detail
        ]
        if not matching:
            raise RuntimeError("Saved address was not returned by repository")

        return max(matching, key=lambda address: address.id or -1)
