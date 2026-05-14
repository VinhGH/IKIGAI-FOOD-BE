from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, TypedDict

from src.modules.iam.domain.entities import Address, User


class RefreshTokenRecord(TypedDict):
    token: str
    user_id: int
    expires_at: datetime
    is_revoked: bool


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        ...

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[User]:
        ...

    @abstractmethod
    async def save(self, user: User) -> User:
        ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool:
        ...

    @abstractmethod
    async def exists_by_phone(self, phone: str) -> bool:
        ...


class AddressRepository(ABC):
    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[Address]:
        ...

    @abstractmethod
    async def save(self, address: Address) -> Address:
        ...

    @abstractmethod
    async def delete(self, address_id: int) -> None:
        ...


class PasswordHasherPort(ABC):
    @abstractmethod
    def hash(self, plain_password: str) -> str:
        ...

    @abstractmethod
    def verify(self, plain_password: str, hashed: str) -> bool:
        ...


class TokenServicePort(ABC):
    @abstractmethod
    def create_access_token(self, user_id: int, role: str) -> str:
        ...

    @abstractmethod
    def create_refresh_token(self, user_id: int) -> str:
        ...

    @abstractmethod
    def verify_access_token(self, token: str) -> dict:
        ...


class RefreshTokenRepository(ABC):
    @abstractmethod
    async def create(self, token: str, user_id: int, expires_at: datetime) -> None:
        ...

    @abstractmethod
    async def get_by_token(self, token: str) -> Optional[RefreshTokenRecord]:
        ...

    @abstractmethod
    async def revoke(self, token: str) -> None:
        ...


class LocationPort(ABC):
    @abstractmethod
    async def resolve_address(
        self,
        province_code: int,
        district_code: int,
        ward_code: int,
    ) -> str:
        """Trả về: 'Số nhà + tên đường, Tên xã, Tên huyện, Tên tỉnh'"""
        ...
