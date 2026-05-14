from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.modules.iam.domain.events import (
    PasswordChanged,
    PasswordResetRequested,
    UserActivated,
    UserRegistered,
)
from src.modules.iam.domain.exceptions import (
    AddressNotFoundException,
    InvalidVerificationCodeException,
    UserAlreadyActiveException,
    UserNotActiveException,
)
from src.modules.iam.domain.value_objects import (
    Email,
    FullName,
    HashedPassword,
    Phone,
    UserRole,
    VerificationCodeType,
)

EMAIL_VERIFICATION_TTL_HOURS = 24
PASSWORD_RESET_TTL_MINUTES = 15


@dataclass
class Address:
    id: Optional[int]
    user_id: Optional[int]
    address_name: str = "Địa chỉ mặc định"
    is_default: bool = False
    province_code: int = 0
    district_code: int = 0
    ward_code: int = 0
    address_detail: str = ""


@dataclass
class VerificationCode:
    id: Optional[int]
    user_id: Optional[int]
    code: str
    code_type: VerificationCodeType
    expires_at: datetime

    def is_valid(self, code: str) -> bool:
        return self.code == code and datetime.now(timezone.utc) < self.expires_at


@dataclass
class UserBase:
    email: Email
    phone: Optional[Phone]
    full_name: FullName
    role: UserRole
    is_active: bool


@dataclass
class User(UserBase):
    id: Optional[int]
    hashed_password: HashedPassword
    created_at: datetime
    addresses: list[Address] = field(default_factory=list)
    verification_codes: list[VerificationCode] = field(default_factory=list)
    _events: list = field(default_factory=list, repr=False)

    @classmethod
    def register(
        cls,
        email: Email,
        full_name: FullName,
        hashed_password: HashedPassword,
        role: UserRole,
        phone: Optional[Phone] = None,
    ) -> "User":
        user = cls(
            id=None,
            email=email,
            phone=phone,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            is_active=False,
            created_at=datetime.now(timezone.utc),
        )
        user._events.append(UserRegistered(email=email.value, role=role.value))
        return user

    def activate(self, code: str) -> None:
        if self.is_active:
            raise UserAlreadyActiveException()

        verification = self._get_valid_code(code, VerificationCodeType.email_verification)
        if not verification:
            raise InvalidVerificationCodeException()

        self.is_active = True
        self._events.append(UserActivated(user_id=self.id, email=self.email.value))

    def request_password_reset(self) -> VerificationCode:
        if not self.is_active:
            raise UserNotActiveException()

        code = self._generate_code(
            code_type=VerificationCodeType.password_reset,
            ttl_minutes=PASSWORD_RESET_TTL_MINUTES,
        )
        self.verification_codes.append(code)
        self._events.append(PasswordResetRequested(user_id=self.id, email=self.email.value))
        return code

    def change_password(
        self,
        new_hashed_password: HashedPassword,
        reset_code: str | None = None,
    ) -> None:
        if reset_code is not None:
            verification = self._get_valid_code(reset_code, VerificationCodeType.password_reset)
            if not verification:
                raise InvalidVerificationCodeException()

        self.hashed_password = new_hashed_password
        self._events.append(PasswordChanged(user_id=self.id, email=self.email.value))

    def add_address(self, address: Address) -> None:
        if address.is_default:
            for existing in self.addresses:
                existing.is_default = False
        self.addresses.append(address)

    def set_default_address(self, address_id: int) -> None:
        found = False
        for address in self.addresses:
            address.is_default = address.id == address_id
            if address.id == address_id:
                found = True

        if not found:
            raise AddressNotFoundException(address_id)

    def create_email_verification_code(self) -> VerificationCode:
        code = self._generate_code(
            code_type=VerificationCodeType.email_verification,
            ttl_minutes=EMAIL_VERIFICATION_TTL_HOURS * 60,
        )
        self.verification_codes.append(code)
        return code

    def _get_valid_code(self, code: str, code_type: VerificationCodeType) -> Optional[VerificationCode]:
        for verification_code in self.verification_codes:
            if verification_code.code_type == code_type and verification_code.is_valid(code):
                return verification_code
        return None

    def _generate_code(self, code_type: VerificationCodeType, ttl_minutes: int) -> VerificationCode:
        import secrets

        return VerificationCode(
            id=None,
            user_id=self.id,
            code=secrets.token_hex(3).upper(),
            code_type=code_type,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )

    def pull_events(self) -> list:
        events, self._events = self._events, []
        return events
