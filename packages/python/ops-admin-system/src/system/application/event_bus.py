from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable

from system.domain.events import DomainEvent


EventHandler = Callable[[DomainEvent], None]


class InMemoryEventBus:
    """Synchronous domain-event bus.

    The interface is intentionally tiny so it can later be backed by an outbox
    table, a task queue, or a broker without changing domain/application code.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._published: list[DomainEvent] = []

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def publish(self, event: DomainEvent) -> None:
        self._published.append(event)
        for handler in self._handlers.get(event.event_type, []):
            handler(event)

    def published_events(self) -> list[DomainEvent]:
        return list(self._published)

    def clear(self) -> None:
        self._published.clear()


event_bus = InMemoryEventBus()


def publish_event(event: DomainEvent) -> None:
    event_bus.publish(event)
