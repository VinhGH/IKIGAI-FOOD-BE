# ARCHITECTURE.md
> **Đây là file "luật bất biến".** AI agents PHẢI đọc file này trước khi viết bất kỳ code nào.
> Không được vi phạm bất kỳ quy tắc nào dưới đây mà không có approval từ human.

---

## 1. Tổng quan hệ thống

Hệ thống food delivery xây dựng theo **Domain-Driven Design (DDD)** kết hợp **Clean Architecture**, chia thành **9 Bounded Contexts** độc lập, chạy trên FastAPI + SQLModel + PostgreSQL.

### Bounded Contexts

| # | Context | Module path | Aggregates chính |
|---|---------|-------------|-----------------|
| 1 | Identity & Access (IAM) | `src/modules/iam` | User, Role |
| 2 | Catalog | `src/modules/catalog` | Restaurant, Dish, Category |
| 3 | Ordering | `src/modules/ordering` | Order, Cart |
| 4 | Payment | `src/modules/payment` | Payment, Transaction |
| 5 | Logistics | `src/modules/logistics` | DeliveryAssignment, ShipmentTracking |
| 6 | Marketing | `src/modules/marketing` | Voucher, Campaign |
| 7 | Feedback | `src/modules/feedback` | Review |
| 8 | Notification | `src/modules/notification` | Notification, Template |
| 9 | Intelligence | `src/modules/intelligence` | Recommendation |

---

## 2. Dependency Rule (QUAN TRỌNG NHẤT)

```
Presentation → Application → Domain ← Infrastructure
```

- `domain/` KHÔNG được import từ bất kỳ layer nào khác trong cùng module
- `domain/` KHÔNG được import từ module khác trực tiếp
- `application/` chỉ được import từ `domain/` của chính module mình
- `infrastructure/` được import `domain/` và các thư viện bên ngoài
- `presentation/` chỉ gọi `application/` thông qua các use case / service

**Vi phạm phổ biến cần tránh:**
```python
# ❌ SAI - domain import SQLModel trực tiếp
from sqlmodel import SQLModel
class Order(SQLModel): ...

# ✅ ĐÚNG - domain là pure Python
class Order:
    def __init__(self, ...): ...

# ❌ SAI - application import từ module khác
from modules.catalog.domain.entities import Restaurant

# ✅ ĐÚNG - dùng adapter interface
from modules.ordering.domain.ports import CatalogPort
```

---

## 3. Cấu trúc thư mục chuẩn (mỗi module)

```
src/modules/{module_name}/
├── domain/
│   ├── entities.py          # Aggregate roots + Entities
│   ├── value_objects.py     # Value Objects (immutable)
│   ├── events.py            # Domain Events
│   ├── exceptions.py        # Domain-specific exceptions
│   └── ports.py             # Repository interfaces + External service interfaces
│
├── application/
│   ├── commands/            # Write operations (mỗi use case = 1 file)
│   │   └── {action}_handler.py
│   ├── queries/             # Read operations (CQRS)
│   │   └── {query}_handler.py
│   ├── dtos.py              # Request/Response DTOs (Pydantic)
│   └── services.py          # Orchestration (nếu cần)
│
├── infrastructure/
│   ├── models.py            # SQLModel table definitions
│   ├── repositories.py      # Concrete repository implementations
│   ├── adapters.py          # Adapter implementations (giao tiếp với module khác)
│   └── event_handlers.py    # Xử lý domain events đến từ module khác
│
└── presentation/
    ├── router.py            # FastAPI router
    └── dependencies.py      # FastAPI dependencies (DI)
```

---

## 4. Giao tiếp giữa các modules

### 4.1 Nguyên tắc

Các module **KHÔNG** được:
- Import trực tiếp `domain/` hoặc `infrastructure/` của module khác
- Truy cập database table của module khác

Các module **ĐƯỢC PHÉP**:
- Publish/subscribe Domain Events qua `EventBus`
- Gọi **Internal Service** của module khác thông qua **Adapter** (viết ở `infrastructure/adapters.py`)

### 4.2 Pattern: Adapter qua Internal Service

```python
# modules/ordering/domain/ports.py
from abc import ABC, abstractmethod

class CatalogPort(ABC):
    """Interface - Ordering chỉ biết đến port này, không biết Catalog implement thế nào"""
    @abstractmethod
    async def get_dish_price(self, dish_id: int) -> Decimal: ...

# modules/ordering/infrastructure/adapters.py
from modules.catalog.application.services import CatalogInternalService

class CatalogAdapter(CatalogPort):
    """Concrete implementation - inject CatalogInternalService"""
    def __init__(self, catalog_service: CatalogInternalService):
        self._svc = catalog_service

    async def get_dish_price(self, dish_id: int) -> Decimal:
        return await self._svc.get_price_for_ordering(dish_id)
```

### 4.3 Domain Events Flow

```
OrderPlaced (Ordering)
    → PaymentContext: khởi tạo giao dịch VNPay
    → NotificationContext: notify nhà hàng

PaymentConfirmed (Payment)
    → OrderingContext: chuyển trạng thái đơn
    → NotificationContext: notify customer

RestaurantConfirmed (Ordering)
    → LogisticsContext: chạy assignment + tracking
    → NotificationContext: notify shipper

OrderCompleted (Ordering)
    → IntelligenceContext: cập nhật recommendation model
    → FeedbackContext: mở khóa review

ReviewSubmitted (Feedback)
    → IntelligenceContext: fine-tune model
```

### 4.4 EventBus

Hiện tại dùng **FastAPI Background Tasks** (đủ cho MVP). Interface:

```python
# src/building_blocks/infrastructure/event_bus.py
class EventBus:
    async def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: type, handler: Callable) -> None: ...
```

Khi scale: swap sang RabbitMQ/Redis Pub-Sub mà không thay đổi domain code.

---

## 5. Database

- Mỗi module có **SQLModel models riêng** trong `infrastructure/models.py`
- **KHÔNG** dùng foreign key cross-module ở tầng ORM (chỉ lưu ID)
- Migration dùng **Alembic**, mỗi module có migration riêng
- Shared DB (PostgreSQL) cho MVP — tách schema sau khi cần

```python
# ❌ SAI - FK cross-module trong ORM
class Order(SQLModel, table=True):
    restaurant: Restaurant = Relationship(...)  # Restaurant thuộc Catalog module

# ✅ ĐÚNG - chỉ lưu ID
class Order(SQLModel, table=True):
    restaurant_id: int  # Chỉ lưu ID, không Relationship
```

---

## 6. Error Handling

Dùng `AppException` + Result pattern, định nghĩa tại `building_blocks`:

```python
# src/building_blocks/exceptions.py
class AppException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code          # Machine-readable: "ORDER_NOT_FOUND"
        self.message = message    # Human-readable (tiếng Việt OK)
        self.status_code = status_code
```

Response format chuẩn cho Frontend:
```json
{
  "success": false,
  "error": {
    "code": "ORDER_NOT_FOUND",
    "message": "Không tìm thấy đơn hàng"
  }
}
```

---

## 7. Authentication & Authorization

- **JWT Access Token**: stateless, short-lived (15 phút)
- **Refresh Token**: lưu DB trong `infrastructure/` của IAM module (KHÔNG phải domain)
- FastAPI `Depends()` inject current user vào route handlers
- Permission check thực hiện ở `application/` layer, không ở `presentation/`

---

## 8. Module đặc biệt: IAM

- `Address`: hiện tại trong IAM, **sẽ migrate sang Profile module** trong tương lai
    - `AddressRepository` interface phải nằm ở `domain/ports.py` để migrate dễ
- `VerificationCode`: domain object, ở `domain/entities.py`
- `RefreshToken`: infra concern, ở `infrastructure/models.py` (KHÔNG phải domain)

---

## 9. Các quyết định chưa finalize (cần human approval trước khi implement)

| Quyết định | Options | Status |
|-----------|---------|--------|
| EventBus production | RabbitMQ vs Redis Pub-Sub | ⏳ Pending |
| Search Catalog | PostgreSQL full-text vs Elasticsearch | ⏳ Pending |
| AI Integration | Gemini API call trực tiếp vs queue | ⏳ Pending |
| Payment sandbox | VNPay sandbox credentials | ⏳ Pending |
