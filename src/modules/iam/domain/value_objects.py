from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum


@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self) -> None:
        value = self.value.lower().strip()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value):
            raise ValueError(f"Email không hợp lệ: {self.value}")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class Phone:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not re.match(r"^0\d{9}$", value):
            raise ValueError(f"Số điện thoại không hợp lệ: {self.value}")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class FullName:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            raise ValueError("Họ tên không được để trống")
        if len(value) > 100:
            raise ValueError("Họ tên không được vượt quá 100 ký tự")
        object.__setattr__(self, "value", value)


@dataclass(frozen=True)
class HashedPassword:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("Hashed password không được rỗng")


@dataclass(frozen=True)
class Money:
    amount: Decimal | int | float | str
    currency: str = "VND"

    def __post_init__(self) -> None:
        amount = self.amount if isinstance(self.amount, Decimal) else Decimal(str(self.amount))
        if amount < 0:
            raise ValueError("Số tiền không được âm")

        currency = self.currency.strip().upper()
        if not currency:
            raise ValueError("Tiền tệ không được rỗng")

        object.__setattr__(self, "amount", amount)
        object.__setattr__(self, "currency", currency)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Không thể cộng hai loại tiền tệ khác nhau")
        return Money(self.amount + other.amount, self.currency)


class UserRole(str, Enum):
    customer = "customer"
    restaurant_owner = "restaurant_owner"
    shipper = "shipper"
    admin = "admin"


class VerificationCodeType(str, Enum):
    email_verification = "email_verification"
    password_reset = "password_reset"
