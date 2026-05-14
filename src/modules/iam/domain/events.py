from dataclasses import dataclass

from building_blocks.domain.events import DomainEvent


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    email: str | None = None
    role: str | None = None


@dataclass(frozen=True)
class UserActivated(DomainEvent):
    user_id: int | None = None
    email: str | None = None


@dataclass(frozen=True)
class PasswordResetRequested(DomainEvent):
    user_id: int | None = None
    email: str | None = None


@dataclass(frozen=True)
class PasswordChanged(DomainEvent):
    user_id: int | None = None
    email: str | None = None
