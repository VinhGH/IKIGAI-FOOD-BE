from __future__ import annotations

import asyncio
from dataclasses import dataclass

from src.modules.iam.application.dtos import AddressResponse
from src.modules.iam.domain.entities import Address
from src.modules.iam.domain.ports import AddressRepository, LocationPort


@dataclass
class ListAddressesQuery:
    address_repo: AddressRepository
    location_port: LocationPort

    async def handle(self, current_user_id: int) -> list[AddressResponse]:
        addresses = await self.address_repo.list_by_user(current_user_id)
        if not addresses:
            return []

        responses = await asyncio.gather(
            *(self._to_response(address) for address in addresses)
        )
        return list(responses)

    async def _to_response(self, address: Address) -> AddressResponse:
        location_address = await self.location_port.resolve_address(
            address.province_code,
            address.district_code,
            address.ward_code,
        )
        full_address = ", ".join(
            part for part in (address.address_detail, location_address) if part
        )
        return AddressResponse.from_domain(address, full_address)
