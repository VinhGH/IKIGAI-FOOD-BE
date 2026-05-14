from collections import defaultdict
from typing import Callable, Type

from ..domain.events import DomainEvent


class EventBus:
    def __init__(self):
        self._handlers: dict = defaultdict(list)

    def subscribe(self, event_type: Type, handler: Callable) -> None:
        self._handlers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers[type(event)]:
            await handler(event)
