import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Event:
    """Domain event in event sourcing pattern."""

    event_type: str
    aggregate_id: str
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EventStore:
    """In-memory event store for demonstrating event sourcing pattern.

    In production, this would be backed by PostgreSQL or a dedicated
    event store (e.g. EventStoreDB). See system-design-demo/ for
    the production architecture.
    """

    def __init__(self) -> None:
        self._events: list[Event] = []

    async def initialize(self) -> None:
        """Initialize event store."""
        logger.info("Event store initialized (in-memory)")

    async def append(self, event: Event) -> None:
        """Append event to store."""
        self._events.append(event)
        logger.info(
            "Event appended: %s for aggregate %s",
            event.event_type,
            event.aggregate_id,
        )

    async def get_events(self, aggregate_id: str) -> list[Event]:
        """Get all events for given aggregate."""
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    async def get_all_aggregate_ids(self) -> list[str]:
        """Get unique aggregate IDs that have events."""
        seen: set[str] = set()
        result: list[str] = []
        for e in self._events:
            if e.aggregate_id not in seen:
                seen.add(e.aggregate_id)
                result.append(e.aggregate_id)
        return result

    async def close(self) -> None:
        """Close event store."""
        logger.info("Event store closed")
