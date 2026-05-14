# MODULE_IAM.md
> AI agents đọc file này để implement IAM module.
> PHẢI đọc `ARCHITECTURE.md` và `CONVENTIONS.md` trước.

---

## 1. Bounded Context Overview

**Trách nhiệm:** Đăng ký, đăng nhập, xác thực, phân quyền cho 4 loại user: Customer, Restaurant Owner, Shipper, Admin.

**KHÔNG thuộc IAM:**
- Thông tin profile chi tiết (bio, avatar) → tương lai: Profile module
- Address → hiện tại tạm ở IAM, **sẽ migrate sang Profile module**
- Business logic của các role (restaurant quản lý menu, shipper nhận đơn) → thuộc module tương ứng

---

## 2. Domain Model

### 2.1 Aggregates & Entities

```
User (Aggregate Root)
├── Address (Entity — owned by User, sẽ migrate)
└── VerificationCode (Entity — owned by User)

RefreshToken → KHÔNG phải domain object → infrastructure/models.py
```

### 2.2 Value Objects

| VO | Validation rules |
|----|-----------------|
| `Email` | format hợp lệ, lowercase, strip whitespace |
| `Phone` | 10 chữ số, bắt đầu bằng 0, chỉ digit |
| `FullName` | không rỗng, max 100 ký tự, strip |
| `HashedPassword` | không rỗng (không validate format — đây là output của bcrypt) |
| `UserRole` | enum: `customer`, `restaurant_owner`, `shipper`, `admin` |
| `VerificationCodeType` | enum: `email_verification`, `password_reset` |

### 2.3 Domain Events

| Event | Trigger | Consumers |
|-------|---------|-----------|
| `UserRegistered` | User.register() | Notification (gửi email verify) |
| `UserActivated` | User.activate() | Notification (gửi welcome) |
| `PasswordResetRequested` | User.request_password_reset() | Notification (gửi OTP) |
| `PasswordChanged` | User.change_password() | Notification (gửi cảnh báo) |

### 2.4 Domain Rules (Business Invariants)

1. Email phải unique trong toàn hệ thống
2. Phone phải unique nếu được cung cấp
3. User mới tạo ra có `is_active = False` — phải verify email mới active
4. `VerificationCode` có TTL: email verification = 24h, password reset = 15 phút
5. Mỗi user chỉ có **1 default address** tại một thời điểm
6. Không thể login nếu `is_active = False`

---

## 3. Domain Layer — Code

### `domain/value_objects.py`

```python
from dataclasses import dataclass
from enum import Enum
import re

@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        value = self.value.lower().strip()
        if not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value):
            raise ValueError(f"Email không hợp lệ: {self.value}")
        object.__setattr__(self, "value", value)

@dataclass(frozen=True)
class Phone:
    value: str

    def __post_init__(self):
        value = self.value.strip()
        if not re.match(r"^0\d{9}$", value):
            raise ValueError(f"Số điện thoại không hợp lệ: {self.value}")
        object.__setattr__(self, "value", value)

@dataclass(frozen=True)
class FullName:
    value: str

    def __post_init__(self):
        value = self.value.strip()
        if not value:
            raise ValueError("Họ tên không được để trống")
        if len(value) > 100:
            raise ValueError("Họ tên không được vượt quá 100 ký tự")
        object.__setattr__(self, "value", value)

@dataclass(frozen=True)
class HashedPassword:
    value: str

    def __post_init__(self):
        if not self.value:
            raise ValueError("Hashed password không được rỗng")

class UserRole(str, Enum):
    customer = "customer"
    restaurant_owner = "restaurant_owner"
    shipper = "shipper"
    admin = "admin"

class VerificationCodeType(str, Enum):
    email_verification = "email_verification"
    password_reset = "password_reset"
```

### `domain/entities.py`

```python
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from modules.iam.domain.value_objects import (
    Email, Phone, FullName, HashedPassword, UserRole, VerificationCodeType
)
from modules.iam.domain.events import (
    UserRegistered, UserActivated, PasswordResetRequested, PasswordChanged
)
from modules.iam.domain.exceptions import (
    UserAlreadyActiveException,
    UserNotActiveException,
    InvalidVerificationCodeException,
    DefaultAddressNotFoundException,
)

# TTL constants
EMAIL_VERIFICATION_TTL_HOURS = 24
PASSWORD_RESET_TTL_MINUTES = 15


@dataclass
class Address:
    """Entity — sẽ migrate sang Profile module trong tương lai"""
    id: Optional[int]
    user_id: int
    address_name: str
    is_default: bool
    province_code: int
    district_code: int
    ward_code: int
    address_detail: str


@dataclass
class VerificationCode:
    """Entity — owned by User"""
    id: Optional[int]
    user_id: int
    code: str
    code_type: VerificationCodeType
    expires_at: datetime

    def is_valid(self, code: str) -> bool:
        return (
            self.code == code
            and datetime.now(timezone.utc) < self.expires_at
        )


@dataclass
class User:
    """Aggregate Root"""
    id: Optional[int]
    email: Email
    phone: Optional[Phone]
    full_name: FullName
    hashed_password: HashedPassword
    role: UserRole
    is_active: bool
    created_at: datetime

    addresses: List[Address] = field(default_factory=list)
    verification_codes: List[VerificationCode] = field(default_factory=list)
    _events: List = field(default_factory=list, repr=False)

    # --- Factory ---

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

    # --- Domain behaviors ---

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

    def change_password(self, new_hashed_password: HashedPassword, reset_code: str) -> None:
        verification = self._get_valid_code(reset_code, VerificationCodeType.password_reset)
        if not verification:
            raise InvalidVerificationCodeException()

        self.hashed_password = new_hashed_password
        self._events.append(PasswordChanged(user_id=self.id, email=self.email.value))

    def add_address(self, address: Address) -> None:
        if address.is_default:
            for addr in self.addresses:
                addr.is_default = False
        self.addresses.append(address)

    def set_default_address(self, address_id: int) -> None:
        found = False
        for addr in self.addresses:
            addr.is_default = (addr.id == address_id)
            if addr.id == address_id:
                found = True
        if not found:
            raise DefaultAddressNotFoundException(address_id)

    def create_email_verification_code(self) -> VerificationCode:
        code = self._generate_code(
            code_type=VerificationCodeType.email_verification,
            ttl_minutes=EMAIL_VERIFICATION_TTL_HOURS * 60,
        )
        self.verification_codes.append(code)
        return code

    # --- Helpers ---

    def _get_valid_code(self, code: str, code_type: VerificationCodeType) -> Optional[VerificationCode]:
        for vc in self.verification_codes:
            if vc.code_type == code_type and vc.is_valid(code):
                return vc
        return None

    def _generate_code(self, code_type: VerificationCodeType, ttl_minutes: int) -> VerificationCode:
        import secrets
        return VerificationCode(
            id=None,
            user_id=self.id,
            code=secrets.token_hex(3).upper(),   # 6 ký tự hex
            code_type=code_type,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes),
        )

    def pull_events(self) -> List:
        events, self._events = self._events, []
        return events
```

### `domain/events.py`

```python
from dataclasses import dataclass
from modules.iam.domain.value_objects import DomainEvent  # từ building_blocks

@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    email: str = None
    role: str = None

@dataclass(frozen=True)
class UserActivated(DomainEvent):
    user_id: int = None
    email: str = None

@dataclass(frozen=True)
class PasswordResetRequested(DomainEvent):
    user_id: int = None
    email: str = None

@dataclass(frozen=True)
class PasswordChanged(DomainEvent):
    user_id: int = None
    email: str = None
```

### `domain/exceptions.py`

```python
from building_blocks.exceptions import AppException

class UserNotFoundException(AppException):
    def __init__(self, identifier: str = ""):
        super().__init__("USER_NOT_FOUND", f"Không tìm thấy người dùng {identifier}", 404)

class EmailAlreadyExistsException(AppException):
    def __init__(self, email: str):
        super().__init__("EMAIL_ALREADY_EXISTS", f"Email {email} đã được sử dụng", 409)

class PhoneAlreadyExistsException(AppException):
    def __init__(self, phone: str):
        super().__init__("PHONE_ALREADY_EXISTS", f"Số điện thoại {phone} đã được sử dụng", 409)

class UserAlreadyActiveException(AppException):
    def __init__(self):
        super().__init__("USER_ALREADY_ACTIVE", "Tài khoản đã được xác thực", 409)

class UserNotActiveException(AppException):
    def __init__(self):
        super().__init__("USER_NOT_ACTIVE", "Tài khoản chưa được xác thực email", 403)

class InvalidVerificationCodeException(AppException):
    def __init__(self):
        super().__init__("INVALID_VERIFICATION_CODE", "Mã xác thực không hợp lệ hoặc đã hết hạn", 400)

class InvalidCredentialsException(AppException):
    def __init__(self):
        super().__init__("INVALID_CREDENTIALS", "Email hoặc mật khẩu không đúng", 401)

class DefaultAddressNotFoundException(AppException):
    def __init__(self, address_id: int):
        super().__init__("ADDRESS_NOT_FOUND", f"Không tìm thấy địa chỉ #{address_id}", 404)
```

### `domain/ports.py`

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from modules.iam.domain.entities import User, Address

class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> Optional[User]: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]: ...

    @abstractmethod
    async def get_by_phone(self, phone: str) -> Optional[User]: ...

    @abstractmethod
    async def save(self, user: User) -> User: ...

    @abstractmethod
    async def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    async def exists_by_phone(self, phone: str) -> bool: ...

class AddressRepository(ABC):
    """
    Interface tách biệt để migrate sang Profile module dễ dàng.
    Khi migrate: chỉ cần move interface này + implementation, không đụng domain User.
    """
    @abstractmethod
    async def list_by_user(self, user_id: int) -> List[Address]: ...

    @abstractmethod
    async def save(self, address: Address) -> Address: ...

    @abstractmethod
    async def delete(self, address_id: int) -> None: ...

class PasswordHasherPort(ABC):
    """Port để hash/verify password — implementation dùng bcrypt ở infra"""
    @abstractmethod
    def hash(self, plain_password: str) -> str: ...

    @abstractmethod
    def verify(self, plain_password: str, hashed: str) -> bool: ...

class TokenServicePort(ABC):
    """Port để tạo/verify JWT — implementation ở infra"""
    @abstractmethod
    def create_access_token(self, user_id: int, role: str) -> str: ...

    @abstractmethod
    def create_refresh_token(self, user_id: int) -> str: ...

    @abstractmethod
    def verify_access_token(self, token: str) -> dict: ...
```

---

## 4. Application Layer — Use Cases

### Danh sách Use Cases

| # | Use Case | Command/Query | Actor |
|---|----------|--------------|-------|
| 1 | Đăng ký tài khoản | Command | Guest |
| 2 | Verify email | Command | Guest |
| 3 | Đăng nhập | Command | Guest |
| 4 | Refresh token | Command | Authenticated |
| 5 | Logout | Command | Authenticated |
| 6 | Yêu cầu reset password | Command | Guest |
| 7 | Reset password | Command | Guest |
| 8 | Đổi password | Command | Authenticated |
| 9 | Lấy thông tin profile | Query | Authenticated |
| 10 | Thêm địa chỉ | Command | Customer |
| 11 | Xoá địa chỉ | Command | Customer |
| 12 | Set default address | Command | Customer |
| 13 | Lấy danh sách địa chỉ | Query | Customer |

### Command: Register

```python
# application/commands/register_handler.py

@dataclass
class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.customer
    phone: Optional[str] = None

@dataclass
class RegisterHandler:
    user_repo: UserRepository
    address_repo: AddressRepository
    password_hasher: PasswordHasherPort
    event_bus: EventBus

    async def handle(self, request: RegisterRequest) -> UserResponse:
        # 1. Check uniqueness
        if await self.user_repo.exists_by_email(request.email):
            raise EmailAlreadyExistsException(request.email)
        if request.phone and await self.user_repo.exists_by_phone(request.phone):
            raise PhoneAlreadyExistsException(request.phone)

        # 2. Build domain objects
        user = User.register(
            email=Email(request.email),
            full_name=FullName(request.full_name),
            hashed_password=HashedPassword(self.password_hasher.hash(request.password)),
            role=request.role,
            phone=Phone(request.phone) if request.phone else None,
        )

        # 3. Tạo verification code
        code = user.create_email_verification_code()

        # 4. Persist
        saved_user = await self.user_repo.save(user)

        # 5. Publish events
        for event in saved_user.pull_events():
            await self.event_bus.publish(event)

        return UserResponse.from_domain(saved_user)
```

### Command: Login

```python
# application/commands/login_handler.py

@dataclass
class LoginRequest(BaseModel):
    email: str
    password: str

@dataclass
class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

@dataclass
class LoginHandler:
    user_repo: UserRepository
    password_hasher: PasswordHasherPort
    token_service: TokenServicePort

    async def handle(self, request: LoginRequest) -> LoginResponse:
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise InvalidCredentialsException()

        if not self.password_hasher.verify(request.password, user.hashed_password.value):
            raise InvalidCredentialsException()

        if not user.is_active:
            raise UserNotActiveException()

        return LoginResponse(
            access_token=self.token_service.create_access_token(user.id, user.role.value),
            refresh_token=self.token_service.create_refresh_token(user.id),
        )
```

---

## 5. Infrastructure Layer

### `infrastructure/models.py`

```python
from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class UserModel(SQLModel, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    phone: Optional[str] = Field(default=None, unique=True)
    full_name: str
    hashed_password: str
    role: str
    is_active: bool = Field(default=False)
    created_at: datetime

    addresses: List["AddressModel"] = Relationship(back_populates="user")
    verification_codes: List["VerificationCodeModel"] = Relationship(back_populates="user")

class AddressModel(SQLModel, table=True):
    __tablename__ = "addresses"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    address_name: str = Field(default="Địa chỉ mặc định")
    is_default: bool = Field(default=False)
    province_code: int          # Chỉ lưu code, không FK sang Location (cross-module)
    district_code: int
    ward_code: int
    address_detail: str
    user: "UserModel" = Relationship(back_populates="addresses")

class VerificationCodeModel(SQLModel, table=True):
    __tablename__ = "verification_codes"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    code: str
    code_type: str
    expires_at: datetime
    user: "UserModel" = Relationship(back_populates="verification_codes")

class RefreshTokenModel(SQLModel, table=True):
    """Infra concern — KHÔNG có đối tác ở domain layer"""
    __tablename__ = "refresh_tokens"
    id: Optional[int] = Field(default=None, primary_key=True)
    token: str = Field(index=True)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime
    expires_at: datetime
    is_revoked: bool = Field(default=False)
```

---

## 6. Presentation Layer — API Routes

### Route table

| Method | Path | Handler | Auth | Role |
|--------|------|---------|------|------|
| POST | `/auth/register` | RegisterHandler | ❌ | - |
| POST | `/auth/verify-email` | VerifyEmailHandler | ❌ | - |
| POST | `/auth/login` | LoginHandler | ❌ | - |
| POST | `/auth/refresh` | RefreshTokenHandler | ❌ | - |
| POST | `/auth/logout` | LogoutHandler | ✅ | Any |
| POST | `/auth/forgot-password` | ForgotPasswordHandler | ❌ | - |
| POST | `/auth/reset-password` | ResetPasswordHandler | ❌ | - |
| PUT | `/auth/change-password` | ChangePasswordHandler | ✅ | Any |
| GET | `/users/me` | GetProfileQuery | ✅ | Any |
| GET | `/users/me/addresses` | ListAddressesQuery | ✅ | Customer |
| POST | `/users/me/addresses` | AddAddressHandler | ✅ | Customer |
| DELETE | `/users/me/addresses/{id}` | DeleteAddressHandler | ✅ | Customer |
| PATCH | `/users/me/addresses/{id}/default` | SetDefaultAddressHandler | ✅ | Customer |

---

## 7. Migration Note (Address → Profile)

Khi Profile module được tạo:
1. Copy `AddressRepository` interface sang `modules/profile/domain/ports.py`
2. Move `AddressRepositoryImpl` sang `modules/profile/infrastructure/repositories.py`
3. Move `AddressModel` sang `modules/profile/infrastructure/models.py`
4. Xoá `Address` khỏi `User` aggregate, tạo `UserProfile` aggregate mới trong Profile module
5. IAM chỉ giữ: authentication + authorization

Không cần thay đổi bất kỳ route hoặc use case nào của IAM.
