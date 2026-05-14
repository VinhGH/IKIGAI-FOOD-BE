from importlib import import_module
import sys

_exceptions = import_module("src.building_blocks.exceptions")
_domain = import_module("src.building_blocks.domain")
_domain_events = import_module("src.building_blocks.domain.events")
_infrastructure = import_module("src.building_blocks.infrastructure")
_event_bus = import_module("src.building_blocks.infrastructure.event_bus")

sys.modules.setdefault("building_blocks.exceptions", _exceptions)
sys.modules.setdefault("building_blocks.domain", _domain)
sys.modules.setdefault("building_blocks.domain.events", _domain_events)
sys.modules.setdefault("building_blocks.infrastructure", _infrastructure)
sys.modules.setdefault("building_blocks.infrastructure.event_bus", _event_bus)

AppException = _exceptions.AppException
DomainEvent = _domain_events.DomainEvent
EventBus = _event_bus.EventBus

__all__ = ["AppException", "DomainEvent", "EventBus"]
