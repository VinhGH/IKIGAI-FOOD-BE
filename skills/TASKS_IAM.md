# TASKS_IAM.md
> Mỗi task = 1 agent run độc lập.
> Agent PHẢI đọc `ARCHITECTURE.md` + `CONVENTIONS.md` + `MODULE_IAM.md` trước khi chạy bất kỳ task nào.
> Tasks có số thứ tự = thứ tự phụ thuộc. Không chạy task N+1 khi task N chưa pass.

---

## Dependency Graph

```
[T01] Building Blocks
        ↓
[T02] IAM Domain Layer
        ↓
[T03] IAM Infrastructure Models
        ↓
[T04] IAM Repositories
        ↓
[T05] Password & Token Services
        ↓
[T06] Register + Verify Email
[T07] Login + Refresh + Logout      ← T05 required
[T08] Forgot/Reset/Change Password  ← T05 required
        ↓
[T09] Profile & Address Handlers    ← T06 required
        ↓
[T10] Presentation Layer (Router)   ← T06+T07+T08+T09 required
        ↓
[T11] Dependency Injection wiring   ← T10 required
        ↓
[T12] Tests                         ← T11 required
```

---

## T01 — Building Blocks

**Mô tả:** Tạo các base class dùng chung cho toàn bộ hệ thống.

**Input files cần đọc:** `ARCHITECTURE.md` section 6, 7

**Files cần tạo:**
```
src/building_blocks/__init__.py
src/building_blocks/exceptions.py
src/building_blocks/domain/events.py
src/building_blocks/infrastructure/event_bus.py
```

**Spec:**

`exceptions.py`:
```python
class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)
```

`domain/events.py`:
```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

`infrastructure/event_bus.py`:
```python
# Dùng FastAPI BackgroundTasks làm bus tạm thời
# Interface phải giữ nguyên khi swap sang RabbitMQ/Redis sau này
from typing import Callable, Type
from collections import defaultdict

class EventBus:
    def __init__(self):
        self._handlers: dict = defaultdict(list)

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            await handler(event)
```

**Acceptance criteria:**
- [ ] `AppException` có thể raise và catch với `code`, `message`, `status_code`
- [ ] `DomainEvent` có `event_id` (UUID) và `occurred_at` (UTC datetime) tự động
- [ ] `EventBus.publish()` gọi đúng handler đã subscribe
- [ ] Import từ `building_blocks.exceptions` và `building_blocks.domain.events` không lỗi

---

## T02 — IAM Domain Layer

**Mô tả:** Implement toàn bộ domain layer của IAM — pure Python, zero framework dependency.

**Input files cần đọc:** `MODULE_IAM.md` sections 2, 3

**Files cần tạo:**
```
src/modules/iam/domain/__init__.py
src/modules/iam/domain/value_objects.py
src/modules/iam/domain/events.py
src/modules/iam/domain/exceptions.py
src/modules/iam/domain/entities.py
src/modules/iam/domain/ports.py
```

**Spec:** Lấy toàn bộ từ `MODULE_IAM.md` section 3.

**Thứ tự viết trong task này:**
1. `value_objects.py` trước (entities phụ thuộc)
2. `events.py` (entities phụ thuộc)
3. `exceptions.py` (entities phụ thuộc)
4. `ports.py` (chỉ dùng ABC, không import infra)
5. `entities.py` cuối cùng

**Acceptance criteria:**
- [ ] Không có bất kỳ `import` nào từ `sqlmodel`, `fastapi`, `pydantic` trong toàn bộ `domain/`
- [ ] `Email("invalid")` raise `ValueError`
- [ ] `Email("TEST@GMAIL.COM").value == "test@gmail.com"`
- [ ] `Phone("0901234567")` không raise
- [ ] `Phone("123")` raise `ValueError`
- [ ] `Money(-1)` raise `ValueError`
- [ ] `User.register(...)` trả về user với `is_active=False`
- [ ] `User.register(...)` push `UserRegistered` event vào `_events`
- [ ] `user.pull_events()` trả về events và xoá khỏi `_events`
- [ ] `user.activate(valid_code)` set `is_active=True`
- [ ] `user.activate(expired_code)` raise `InvalidVerificationCodeException`
- [ ] `user.activate(...)` khi đã active raise `UserAlreadyActiveException`
- [ ] `VerificationCode.is_valid()` trả `False` khi hết hạn
- [ ] `Address` là dataclass bình thường, không có SQLModel

---

## T03 — IAM Infrastructure Models

**Mô tả:** Tạo SQLModel table definitions cho IAM. TÁCH BIỆT hoàn toàn với domain entities.

**Input files cần đọc:** `MODULE_IAM.md` section 5, `CONVENTIONS.md` section 4

**Files cần tạo:**
```
src/modules/iam/infrastructure/__init__.py
src/modules/iam/infrastructure/models.py
```

**Spec:** Lấy từ `MODULE_IAM.md` section 5 `infrastructure/models.py`.

**Constraints bắt buộc:**
- `province_code`, `district_code`, `ward_code` trong `AddressModel`: chỉ lưu integer, KHÔNG có `Relationship` sang bất kỳ Location model nào
- `RefreshTokenModel` KHÔNG có domain entity tương ứng — đây là infra-only
- Tất cả `__tablename__` phải là snake_case, số nhiều: `users`, `addresses`, `verification_codes`, `refresh_tokens`

**Acceptance criteria:**
- [ ] `from modules.iam.infrastructure.models import UserModel` không lỗi
- [ ] `UserModel.__tablename__ == "users"`
- [ ] `AddressModel` không có `Relationship` sang Location module
- [ ] `RefreshTokenModel` tồn tại và có các fields: `token`, `user_id`, `expires_at`, `is_revoked`
- [ ] Không có domain import nào trong `models.py` (không import từ `domain/`)

---

## T04 — IAM Repositories

**Mô tả:** Implement concrete repositories — mapping giữa SQLModel models và domain entities.

**Input files cần đọc:** `MODULE_IAM.md` section 5, `CONVENTIONS.md` section 4

**Depends on:** T02, T03

**Files cần tạo:**
```
src/modules/iam/infrastructure/repositories.py
```

**Spec:**

Implement `UserRepository` (từ `domain/ports.py`):
- `get_by_id(user_id)` → eager load `addresses` + `verification_codes`
- `get_by_email(email)` → eager load như trên
- `get_by_phone(phone)` → eager load như trên
- `save(user)` → upsert: nếu `user.id is None` thì insert, ngược lại update
- `exists_by_email(email)` → dùng `SELECT EXISTS` không load toàn bộ object
- `exists_by_phone(phone)` → tương tự

Implement `AddressRepository` (từ `domain/ports.py`):
- `list_by_user(user_id)` → list tất cả address của user
- `save(address)` → upsert
- `delete(address_id)` → hard delete

**Mapping rule bắt buộc:**
```python
# _to_domain(): SQLModel model → domain entity
# _to_model(): domain entity → SQLModel model
# Hai method này là private, chỉ dùng trong class
```

**Acceptance criteria:**
- [ ] `UserRepositoryImpl` implement đủ abstract methods của `UserRepository`
- [ ] `AddressRepositoryImpl` implement đủ abstract methods của `AddressRepository`
- [ ] `save(user)` với `user.id=None` → INSERT, trả về user có `id` được gán
- [ ] `save(user)` với `user.id=5` → UPDATE
- [ ] `get_by_email()` load kèm `verification_codes` (không gây N+1)
- [ ] `_to_domain()` và `_to_model()` là private method
- [ ] Không có business logic trong repository (chỉ persistence)

**Process note for implementation and review**
- Reusable notes are split by task type in `IMPLEMENTATION_EXPERIENCES.md`.
- For repository work, read the matching chunk before editing:
  - `skills/implementation_experiences/orm_typing.md`
  - `skills/implementation_experiences/optional_id_boundary.md`
  - `skills/implementation_experiences/strict_return_boundary.md`

---

## T05 — Password Hasher & Token Service

**Mô tả:** Implement infra services cho password hashing (bcrypt) và JWT tokens.

**Depends on:** T02

**Files cần tạo:**
```
src/modules/iam/infrastructure/security.py
```

**Spec:**

`BcryptPasswordHasher` implement `PasswordHasherPort`:
- Dùng thư viện `bcrypt` (đã có trong venv)
- `hash(plain)` → bcrypt hash string
- `verify(plain, hashed)` → bool

`JWTTokenService` implement `TokenServicePort`:
- Dùng thư viện `python-jose` (đã có trong venv: `jose`)
- Access token payload: `{"sub": str(user_id), "role": role, "type": "access"}`
- Refresh token payload: `{"sub": str(user_id), "type": "refresh"}`
- Algorithm: `HS256`
- Secret key đọc từ env: `JWT_SECRET_KEY`
- Access token TTL: `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default: 15)
- Refresh token TTL: `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default: 30)
- `verify_access_token(token)` → raise `AppException(code="INVALID_TOKEN", status_code=401)` nếu invalid/expired

**Env vars cần có trong `.env`:**
```
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=15
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

**Acceptance criteria:**
- [ ] `hasher.verify(plain, hasher.hash(plain)) == True`
- [ ] `hasher.verify("wrong", hasher.hash("correct")) == False`
- [ ] `token_service.create_access_token(1, "customer")` trả về JWT string
- [ ] Decode access token có `sub="1"`, `role="customer"`, `type="access"`
- [ ] `token_service.verify_access_token(expired_token)` raise `AppException` với `code="TOKEN_EXPIRED"`
- [ ] `token_service.verify_access_token("garbage")` raise `AppException` với `code="INVALID_TOKEN"`

---

## T06 — Register + Verify Email Handlers

**Mô tả:** Implement command handlers cho đăng ký và xác thực email.

**Input files cần đọc:** `MODULE_IAM.md` section 4, `API_CONTRACT_IAM.md` endpoints 1-2

**Depends on:** T02, T04, T05

**Files cần tạo:**
```
src/modules/iam/application/__init__.py
src/modules/iam/application/dtos.py          ← thêm RegisterRequest, VerifyEmailRequest, UserResponse
src/modules/iam/application/commands/register_handler.py
src/modules/iam/application/commands/verify_email_handler.py
```

**Spec `RegisterHandler`:** Lấy từ `MODULE_IAM.md` section 4.

**Spec `VerifyEmailHandler`:**
```python
@dataclass
class VerifyEmailRequest(BaseModel):
    email: str
    code: str

@dataclass
class VerifyEmailHandler:
    user_repo: UserRepository
    event_bus: EventBus

    async def handle(self, request: VerifyEmailRequest) -> dict:
        user = await self.user_repo.get_by_email(request.email)
        if not user:
            raise UserNotFoundException(request.email)

        user.activate(request.code)   # raises nếu invalid

        await self.user_repo.save(user)
        for event in user.pull_events():
            await self.event_bus.publish(event)

        return {"message": "Xác thực email thành công. Bạn có thể đăng nhập."}
```

**Acceptance criteria:**
- [ ] `RegisterHandler.handle()` với email mới → trả `UserResponse` với `is_active=False`
- [ ] `RegisterHandler.handle()` với email trùng → raise `EmailAlreadyExistsException`
- [ ] `RegisterHandler.handle()` với phone trùng → raise `PhoneAlreadyExistsException`
- [ ] Sau register, `UserRegistered` event được publish
- [ ] `VerifyEmailHandler.handle()` với code đúng → user `is_active=True` được save
- [ ] `VerifyEmailHandler.handle()` với code sai → raise `InvalidVerificationCodeException`
- [ ] `VerifyEmailHandler.handle()` với user đã active → raise `UserAlreadyActiveException`

---

## T07 — Login + Refresh + Logout Handlers

**Mô tả:** Implement authentication flow handlers.

**Input files cần đọc:** `API_CONTRACT_IAM.md` endpoints 3-5

**Depends on:** T02, T04, T05

**Files cần tạo:**
```
src/modules/iam/application/dtos.py          ← thêm LoginRequest, LoginResponse, RefreshRequest
src/modules/iam/application/commands/login_handler.py
src/modules/iam/application/commands/refresh_token_handler.py
src/modules/iam/application/commands/logout_handler.py
```

**Spec `LoginHandler`:** Lấy từ `MODULE_IAM.md` section 4.

**Spec `RefreshTokenHandler`:**
- Nhận `refresh_token` string
- Verify token hợp lệ (dùng `TokenServicePort.verify_access_token` với type check `"refresh"`)
- Kiểm tra token chưa bị revoke trong `RefreshTokenModel`
- Tạo access token mới
- Trả `{"access_token": ..., "token_type": "bearer"}`

**Spec `LogoutHandler`:**
- Nhận `refresh_token` string
- Set `is_revoked=True` trong `RefreshTokenModel`
- Không raise lỗi dù token không tồn tại (idempotent)

**Acceptance criteria:**
- [ ] `LoginHandler` với credentials đúng → trả `LoginResponse` có `access_token` + `refresh_token` + `user`
- [ ] `LoginHandler` với password sai → raise `InvalidCredentialsException`
- [ ] `LoginHandler` với user chưa active → raise `UserNotActiveException`
- [ ] `RefreshTokenHandler` với refresh token hợp lệ → trả access token mới
- [ ] `RefreshTokenHandler` với token đã revoke → raise `AppException(code="TOKEN_REVOKED")`
- [ ] `LogoutHandler` set `is_revoked=True` trong DB
- [ ] `LogoutHandler` không raise khi token không tồn tại

---

## T08 — Forgot/Reset/Change Password Handlers

**Mô tả:** Implement password management handlers.

**Input files cần đọc:** `API_CONTRACT_IAM.md` endpoints 6-8

**Depends on:** T02, T04, T05

**Files cần tạo:**
```
src/modules/iam/application/dtos.py          ← thêm ForgotPasswordRequest, ResetPasswordRequest, ChangePasswordRequest
src/modules/iam/application/commands/forgot_password_handler.py
src/modules/iam/application/commands/reset_password_handler.py
src/modules/iam/application/commands/change_password_handler.py
```

**Spec `ForgotPasswordHandler`:**
- Tìm user theo email
- Nếu không tìm thấy → **KHÔNG raise**, trả message bình thường (tránh enumeration)
- Nếu tìm thấy → gọi `user.request_password_reset()` → publish `PasswordResetRequested`
- Save user (VerificationCode mới được thêm vào)

**Spec `ResetPasswordHandler`:**
- Tìm user theo email → raise `UserNotFoundException` nếu không có
- Gọi `user.change_password(new_hashed, reset_code)`
- Save + publish events

**Spec `ChangePasswordHandler`:**
- Nhận thêm `current_user_id` (từ JWT, không từ request body)
- Verify `current_password` bằng `PasswordHasherPort`
- Nếu sai → raise `InvalidCredentialsException`
- Gọi `user.change_password(new_hashed, ...)` — lưu ý: change password flow khác reset (không cần OTP, dùng current password để verify)
- Điều chỉnh domain method nếu cần

**Acceptance criteria:**
- [ ] `ForgotPasswordHandler` với email không tồn tại → trả message bình thường, KHÔNG raise
- [ ] `ForgotPasswordHandler` với email hợp lệ → `PasswordResetRequested` event được publish
- [ ] `ResetPasswordHandler` với OTP đúng → password được thay đổi
- [ ] `ResetPasswordHandler` với OTP sai/hết hạn → raise `InvalidVerificationCodeException`
- [ ] `ChangePasswordHandler` với current_password sai → raise `InvalidCredentialsException`
- [ ] `ChangePasswordHandler` thành công → `PasswordChanged` event được publish

---

## T09 — Profile & Address Handlers

**Mô tả:** Implement query/command handlers cho profile và address management.

**Input files cần đọc:** `API_CONTRACT_IAM.md` endpoints 9-13

**Depends on:** T02, T04, T06

**Files cần tạo:**
```
src/modules/iam/application/dtos.py          ← thêm AddressRequest, AddressResponse, ProfileResponse
src/modules/iam/application/queries/get_profile_query.py
src/modules/iam/application/queries/list_addresses_query.py
src/modules/iam/application/commands/add_address_handler.py
src/modules/iam/application/commands/delete_address_handler.py
src/modules/iam/application/commands/set_default_address_handler.py
```

**Spec `AddressResponse`:**
```python
class AddressResponse(BaseModel):
    id: int
    address_name: str
    is_default: bool
    province_code: int
    district_code: int
    ward_code: int
    address_detail: str
    full_address: str   # BE join tên từ Location module trước khi trả về
```

**Lưu ý `full_address`:** Handler cần gọi `LocationPort` (adapter) để resolve `province_code`, `district_code`, `ward_code` thành tên đầy đủ. Tạo `LocationPort` interface trong `domain/ports.py`:
```python
class LocationPort(ABC):
    @abstractmethod
    async def resolve_address(self, province_code: int, district_code: int, ward_code: int) -> str:
        """Trả về: 'Số nhà + tên đường, Tên xã, Tên huyện, Tên tỉnh'"""
        ...
```

**Acceptance criteria:**
- [ ] `GetProfileQuery` trả đúng `ProfileResponse` từ user hiện tại
- [ ] `ListAddressesQuery` trả list `AddressResponse` có `full_address` được resolve
- [ ] `AddAddressHandler` với `is_default=True` → các address khác có `is_default=False`
- [ ] `SetDefaultAddressHandler` với address không thuộc user → raise `AddressNotFoundException`
- [ ] `DeleteAddressHandler` với address không thuộc user → raise `AddressNotFoundException`
- [ ] `LocationPort` là abstract interface, chưa cần implementation thật (mock trong test)

---

## T10 — Presentation Layer (Router)

**Mô tả:** Tạo FastAPI router kết nối tất cả handlers với HTTP endpoints.

**Input files cần đọc:** `API_CONTRACT_IAM.md` toàn bộ, `MODULE_IAM.md` section 6

**Depends on:** T06, T07, T08, T09

**Files cần tạo:**
```
src/modules/iam/presentation/__init__.py
src/modules/iam/presentation/router.py
src/modules/iam/presentation/dependencies.py
```

**Spec `router.py`:** 13 endpoints theo đúng bảng trong `MODULE_IAM.md` section 6.

**Spec `dependencies.py`:**
```python
# FastAPI dependency functions
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Verify JWT, trả về domain User. Raise 401 nếu invalid."""
    ...

async def require_customer(current_user: User = Depends(get_current_user)) -> User:
    """Raise 403 nếu role không phải customer."""
    ...

async def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Raise 403 nếu role không phải admin."""
    ...
```

**Response format bắt buộc:** Tất cả response wrap trong:
```python
{"success": True, "data": ...}   # thành công
{"success": False, "error": {"code": ..., "message": ...}}  # lỗi
```

Dùng FastAPI `exception_handler` để catch `AppException` và format tự động.

**Acceptance criteria:**
- [ ] `POST /auth/register` → gọi `RegisterHandler`
- [ ] `POST /auth/login` → gọi `LoginHandler`
- [ ] `GET /users/me` yêu cầu valid JWT, trả 401 nếu thiếu
- [ ] `POST /users/me/addresses` yêu cầu role `customer`, trả 403 nếu role khác
- [ ] Tất cả `AppException` được catch và format đúng `{"success": false, "error": {...}}`
- [ ] Router có prefix `/v1` hoặc được mount với prefix từ `main.py`

---

## T11 — Dependency Injection Wiring

**Mô tả:** Kết nối tất cả dependencies — repositories, services, handlers — vào FastAPI app.

**Depends on:** T10

**Files cần tạo/sửa:**
```
src/modules/iam/presentation/dependencies.py   ← bổ sung factory functions
src/apps/main.py                               ← mount IAM router
src/building_blocks/infrastructure/database.py ← SQLModel engine + session
```

**Spec `database.py`:**
```python
# Đọc DATABASE_URL từ env
# Tạo async engine với asyncpg
# Tạo get_session() dependency cho FastAPI
```

**Env vars cần có:**
```
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
```

**Wiring pattern:**
```python
# dependencies.py
def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    return UserRepositoryImpl(session)

def get_register_handler(
    user_repo: UserRepository = Depends(get_user_repository),
    event_bus: EventBus = Depends(get_event_bus),
    password_hasher: PasswordHasherPort = Depends(get_password_hasher),
) -> RegisterHandler:
    return RegisterHandler(user_repo, password_hasher, event_bus)
```

**Acceptance criteria:**
- [ ] `uvicorn src.apps.main:app` chạy không lỗi
- [ ] `GET /v1/docs` hiển thị Swagger UI với 13 IAM endpoints
- [ ] Database connection thành công với `DATABASE_URL` hợp lệ
- [ ] Session được close đúng cách sau mỗi request (không leak)

---

## T12 — Tests

**Mô tả:** Viết unit tests cho domain layer và integration tests cho handlers.

**Depends on:** T11

**Files cần tạo:**
```
tests/modules/iam/domain/test_entities.py
tests/modules/iam/domain/test_value_objects.py
tests/modules/iam/application/test_register_handler.py
tests/modules/iam/application/test_login_handler.py
```

**Test coverage bắt buộc (domain):**

`test_value_objects.py`:
- Email validation (valid, invalid format, uppercase → lowercase)
- Phone validation (valid 10 digits, invalid length, non-digit)
- Money validation (negative raise, addition same currency)

`test_entities.py`:
- `User.register()` → `is_active=False`, push `UserRegistered`
- `user.activate()` → happy path, expired code, already active
- `user.request_password_reset()` → push event, thêm VerificationCode
- `user.add_address()` với `is_default=True` → unset các address khác

**Test pattern (dùng mock):**
```python
# Dùng pytest + pytest-asyncio + unittest.mock
from unittest.mock import AsyncMock, MagicMock

async def test_register_success():
    user_repo = AsyncMock(spec=UserRepository)
    user_repo.exists_by_email.return_value = False
    user_repo.exists_by_phone.return_value = False
    user_repo.save.return_value = fake_user

    handler = RegisterHandler(user_repo, mock_hasher, mock_event_bus)
    result = await handler.handle(RegisterRequest(...))

    assert result.is_active == False
    mock_event_bus.publish.assert_called_once()
```

**Acceptance criteria:**
- [ ] `pytest tests/modules/iam/` chạy không lỗi
- [ ] Coverage domain layer ≥ 80%
- [ ] Không có test nào kết nối DB thật (dùng mock hoàn toàn cho unit tests)
- [ ] Test file không import từ `infrastructure/` hoặc `presentation/`

---

## Checklist hoàn thành IAM module

```
[ ] T01 Building Blocks         — pass all acceptance criteria
[ ] T02 Domain Layer            — pass all acceptance criteria
[ ] T03 Infrastructure Models   — pass all acceptance criteria
[ ] T04 Repositories            — pass all acceptance criteria
[ ] T05 Password & Token        — pass all acceptance criteria
[ ] T06 Register + Verify       — pass all acceptance criteria
[ ] T07 Login + Refresh + Logout— pass all acceptance criteria
[ ] T08 Password Management     — pass all acceptance criteria
[ ] T09 Profile & Address       — pass all acceptance criteria
[ ] T10 Presentation Layer      — pass all acceptance criteria
[ ] T11 DI Wiring               — uvicorn chạy được, Swagger hiển thị đủ 13 endpoints
[ ] T12 Tests                   — pytest pass, coverage ≥ 80%
```

Khi toàn bộ checklist trên xanh → IAM module hoàn thành → bắt đầu MODULE_CATALOG.
