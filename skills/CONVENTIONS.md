# CONVENTIONS.md

> AI agents PHẢI follow file này khi sinh code. Mỗi mục có ví dụ ✅ ĐÚNG và ❌ SAI.

---

## 0. Complition Conditions

- 1 Task được cho là hoàn thành khi nó chạy lệnh 'ruff check' không còn phát hiện lỗi.
- 2 Nếu lỗi sửa 3 lần ko fix được - tạm bỏ qua sau đó viết báo cá(đủ dùng, không quá dài và không quá thiếu context để tôi tự fix) về lỗi đó khi done task.
- 3 Khi done task, ngoài báo cáo các lỗi chưa fix được, hãy báo cáo những gì đã làm, đã thay đổi lại. Viết ngắn thôi, không cần dài.

## 1. Naming Conventions

### Files & Directories

```
snake_case cho tất cả file .py
PascalCase cho class
SCREAMING_SNAKE cho constants
camelCase KHÔNG dùng trong Python
```

### Classes theo layer

| Layer                | Pattern                 | Ví dụ                                      |
| -------------------- | ----------------------- | ------------------------------------------ |
| Aggregate/Entity     | `{Name}`                | `Order`, `User`, `Dish`                    |
| Value Object         | `{Name}`                | `Email`, `Money`, `Address`                |
| Domain Event         | `{Name}Past`            | `OrderPlaced`, `PaymentConfirmed`          |
| Repository Interface | `{Name}Repository`      | `OrderRepository`                          |
| External Port        | `{Name}Port`            | `CatalogPort`, `PaymentGatewayPort`        |
| Repository Impl      | `{Name}RepositoryImpl`  | `OrderRepositoryImpl`                      |
| Adapter              | `{Name}Adapter`         | `CatalogAdapter`                           |
| Command              | `{Action}{Name}Command` | `CreateOrderCommand`, `CancelOrderCommand` |
| Command Handler      | `{Action}{Name}Handler` | `CreateOrderHandler`                       |
| Query                | `Get{Name}Query`        | `GetOrderQuery`, `ListOrdersQuery`         |
| DTO Request          | `{Action}{Name}Request` | `CreateOrderRequest`                       |
| DTO Response         | `{Name}Response`        | `OrderResponse`, `OrderDetailResponse`     |

---

## 2. Domain Layer

### Aggregate Root

```python
# ✅ ĐÚNG: Pure Python, không import SQLModel, không import infra
# modules/ordering/domain/entities.py

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from modules.ordering.domain.events import OrderPlaced, OrderCancelled
from modules.ordering.domain.exceptions import OrderCannotBeCancelledException
from modules.ordering.domain.value_objects import Money, OrderStatus

@dataclass
class OrderItem:
    dish_id: int
    dish_name: str          # snapshot tại thời điểm đặt, không FK sang Catalog
    quantity: int
    unit_price: Money

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)

@dataclass
class Order:
    """Aggregate Root"""
    id: Optional[int]
    customer_id: int
    restaurant_id: int
    items: List[OrderItem]
    status: OrderStatus
    created_at: datetime

    # Domain events pending publish
    _events: List = field(default_factory=list, repr=False)

    @classmethod
    def create(cls, customer_id: int, restaurant_id: int, items: List[OrderItem]) -> "Order":
        order = cls(
            id=None,
            customer_id=customer_id,
            restaurant_id=restaurant_id,
            items=items,
            status=OrderStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        order._events.append(OrderPlaced(order_id=order.id, customer_id=customer_id))
        return order

    def cancel(self, reason: str) -> None:
        if self.status not in (OrderStatus.PENDING, OrderStatus.CONFIRMED):
            raise OrderCannotBeCancelledException(
                f"Không thể huỷ đơn ở trạng thái {self.status.value}"
            )
        self.status = OrderStatus.CANCELLED
        self._events.append(OrderCancelled(order_id=self.id, reason=reason))

    def pull_events(self) -> List:
        events, self._events = self._events, []
        return events
```

### Value Object

```python
# ✅ ĐÚNG: Immutable, có validation, không có identity
# modules/ordering/domain/value_objects.py

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

@dataclass(frozen=True)   # frozen=True = immutable
class Money:
    amount: Decimal
    currency: str = "VND"

    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Số tiền không được âm")

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError("Không thể cộng hai loại tiền tệ khác nhau")
        return Money(self.amount + other.amount, self.currency)

@dataclass(frozen=True)
class Email:
    value: str

    def __post_init__(self):
        if "@" not in self.value:
            raise ValueError(f"Email không hợp lệ: {self.value}")
        object.__setattr__(self, "value", self.value.lower().strip())

class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY = "ready"
    DELIVERING = "delivering"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
```

### Domain Events

```python
# modules/ordering/domain/events.py

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID, uuid4

@dataclass(frozen=True)
class DomainEvent:
    event_id: UUID = None
    occurred_at: datetime = None

    def __post_init__(self):
        object.__setattr__(self, "event_id", uuid4())
        object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))

@dataclass(frozen=True)
class OrderPlaced(DomainEvent):
    order_id: int = None
    customer_id: int = None

@dataclass(frozen=True)
class OrderCancelled(DomainEvent):
    order_id: int = None
    reason: str = None
```

### Repository Interface (Port)

```python
# modules/ordering/domain/ports.py

from abc import ABC, abstractmethod
from typing import Optional, List
from modules.ordering.domain.entities import Order

class OrderRepository(ABC):
    @abstractmethod
    async def get_by_id(self, order_id: int) -> Optional[Order]: ...

    @abstractmethod
    async def save(self, order: Order) -> Order: ...

    @abstractmethod
    async def list_by_customer(self, customer_id: int) -> List[Order]: ...

class CatalogPort(ABC):
    """Port để Ordering gọi sang Catalog — Ordering chỉ biết interface này"""
    @abstractmethod
    async def get_dish_snapshot(self, dish_id: int) -> dict: ...
    # Returns: {"dish_id": int, "name": str, "price": Decimal, "restaurant_id": int}
```

---

## 3. Application Layer

### Command Handler

```python
# modules/ordering/application/commands/create_order_handler.py

from dataclasses import dataclass
from decimal import Decimal
from modules.ordering.domain.entities import Order, OrderItem
from modules.ordering.domain.ports import OrderRepository, CatalogPort
from modules.ordering.domain.value_objects import Money
from modules.ordering.application.dtos import CreateOrderRequest, OrderResponse
from building_blocks.infrastructure.event_bus import EventBus

@dataclass
class CreateOrderHandler:
    order_repo: OrderRepository
    catalog_port: CatalogPort
    event_bus: EventBus

    async def handle(self, request: CreateOrderRequest) -> OrderResponse:
        # 1. Validate + build domain objects
        items = []
        for item_req in request.items:
            snapshot = await self.catalog_port.get_dish_snapshot(item_req.dish_id)
            items.append(OrderItem(
                dish_id=snapshot["dish_id"],
                dish_name=snapshot["name"],
                quantity=item_req.quantity,
                unit_price=Money(Decimal(str(snapshot["price"]))),
            ))

        # 2. Call domain logic
        order = Order.create(
            customer_id=request.customer_id,
            restaurant_id=request.restaurant_id,
            items=items,
        )

        # 3. Persist
        saved_order = await self.order_repo.save(order)

        # 4. Publish domain events
        for event in saved_order.pull_events():
            await self.event_bus.publish(event)

        return OrderResponse.from_domain(saved_order)
```

### DTOs

```python
# modules/ordering/application/dtos.py

from pydantic import BaseModel
from decimal import Decimal
from typing import List
from modules.ordering.domain.entities import Order

class OrderItemRequest(BaseModel):
    dish_id: int
    quantity: int

class CreateOrderRequest(BaseModel):
    customer_id: int
    restaurant_id: int
    items: List[OrderItemRequest]

class OrderItemResponse(BaseModel):
    dish_id: int
    dish_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

class OrderResponse(BaseModel):
    id: int
    status: str
    total_amount: Decimal
    items: List[OrderItemResponse]

    @classmethod
    def from_domain(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            status=order.status.value,
            total_amount=sum(i.subtotal.amount for i in order.items),
            items=[
                OrderItemResponse(
                    dish_id=i.dish_id,
                    dish_name=i.dish_name,
                    quantity=i.quantity,
                    unit_price=i.unit_price.amount,
                    subtotal=i.subtotal.amount,
                )
                for i in order.items
            ],
        )
```

---

## 4. Infrastructure Layer

### SQLModel Models

```python
# modules/ordering/infrastructure/models.py
# Chú ý: file này TÁCH BIỆT với domain entities

from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

class OrderItemModel(SQLModel, table=True):
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    dish_id: int                  # Chỉ lưu ID, không Relationship sang Catalog
    dish_name: str                # Snapshot
    quantity: int
    unit_price: float
    order: "OrderModel" = Relationship(back_populates="items")

class OrderModel(SQLModel, table=True):
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int              # Chỉ lưu ID, không Relationship sang IAM
    restaurant_id: int            # Chỉ lưu ID, không Relationship sang Catalog
    status: str = Field(default="pending")
    created_at: datetime
    items: List[OrderItemModel] = Relationship(back_populates="order")
```

### Repository Implementation

```python
# modules/ordering/infrastructure/repositories.py

from sqlmodel import Session, select
from modules.ordering.domain.entities import Order, OrderItem
from modules.ordering.domain.ports import OrderRepository
from modules.ordering.domain.value_objects import Money, OrderStatus
from modules.ordering.infrastructure.models import OrderModel, OrderItemModel
from decimal import Decimal

class OrderRepositoryImpl(OrderRepository):
    def __init__(self, session: Session):
        self._session = session

    async def get_by_id(self, order_id: int) -> Order | None:
        model = self._session.get(OrderModel, order_id)
        if not model:
            return None
        return self._to_domain(model)

    async def save(self, order: Order) -> Order:
        model = self._to_model(order)
        self._session.add(model)
        self._session.commit()
        self._session.refresh(model)
        return self._to_domain(model)

    def _to_domain(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            customer_id=model.customer_id,
            restaurant_id=model.restaurant_id,
            status=OrderStatus(model.status),
            created_at=model.created_at,
            items=[
                OrderItem(
                    dish_id=i.dish_id,
                    dish_name=i.dish_name,
                    quantity=i.quantity,
                    unit_price=Money(Decimal(str(i.unit_price))),
                )
                for i in model.items
            ],
        )

    def _to_model(self, order: Order) -> OrderModel:
        model = OrderModel(
            id=order.id,
            customer_id=order.customer_id,
            restaurant_id=order.restaurant_id,
            status=order.status.value,
            created_at=order.created_at,
        )
        model.items = [
            OrderItemModel(
                dish_id=i.dish_id,
                dish_name=i.dish_name,
                quantity=i.quantity,
                unit_price=float(i.unit_price.amount),
            )
            for i in order.items
        ]
        return model
```

---

## 5. Presentation Layer

```python
# modules/ordering/presentation/router.py

from fastapi import APIRouter, Depends, HTTPException, status
from modules.ordering.application.commands.create_order_handler import CreateOrderHandler
from modules.ordering.application.dtos import CreateOrderRequest, OrderResponse
from modules.ordering.presentation.dependencies import get_create_order_handler, get_current_user
from building_blocks.exceptions import AppException

router = APIRouter(prefix="/orders", tags=["Ordering"])

@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    request: CreateOrderRequest,
    handler: CreateOrderHandler = Depends(get_create_order_handler),
    current_user = Depends(get_current_user),
):
    try:
        request.customer_id = current_user.id   # override từ JWT
        return await handler.handle(request)
    except AppException as e:
        raise HTTPException(status_code=e.status_code, detail={"code": e.code, "message": e.message})
```

---

## 6. Exception Conventions

```python
# modules/ordering/domain/exceptions.py
from building_blocks.exceptions import AppException

class OrderNotFoundException(AppException):
    def __init__(self, order_id: int):
        super().__init__(
            code="ORDER_NOT_FOUND",
            message=f"Không tìm thấy đơn hàng #{order_id}",
            status_code=404,
        )

class OrderCannotBeCancelledException(AppException):
    def __init__(self, reason: str):
        super().__init__(
            code="ORDER_CANNOT_BE_CANCELLED",
            message=reason,
            status_code=422,
        )
```

---

## 7. Checklist cho AI agents trước khi submit code

- [ ] Domain entities không import `sqlmodel`, `fastapi`, hoặc bất kỳ infra library nào
- [ ] Value Objects có `frozen=True`
- [ ] Domain Events có `frozen=True` và kế thừa `DomainEvent`
- [ ] Repository chỉ thông qua interface (port), không gọi session trực tiếp ở application layer
- [ ] Cross-module chỉ qua Adapter, không import domain của module khác
- [ ] DTOs dùng Pydantic `BaseModel`, không dùng SQLModel
- [ ] SQLModel models chỉ nằm ở `infrastructure/models.py`
- [ ] FK cross-module KHÔNG có `Relationship()`, chỉ lưu `_id`
- [ ] Exceptions kế thừa `AppException` với `code` dạng SCREAMING_SNAKE
- [ ] Domain events được publish qua `EventBus` SAU KHI persist thành công
