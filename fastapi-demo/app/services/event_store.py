from typing import List, Dict, Any
from datetime import datetime, timezone

class Event:
    """Event representing a domain event in event sourcing."""
    
    def __init__(self, event_type: str, aggregate_id: str, data: Dict[str, Any]) -> None:
        self.event_type: str = event_type
        self.aggregate_id: str = aggregate_id
        self.data: Dict[str, Any] = data
        self.timestamp: datetime = datetime.now(timezone.utc)

class EventStore:
    """In-memory event store for event sourcing pattern."""
    
    def __init__(self) -> None:
        self._events: List[Event] = []
    
    async def initialize(self) -> None:
        """Initialize event store."""
        pass
    
    async def append(self, event: Event) -> None:
        """Append event to store."""
        self._events.append(event)
    
    async def get_events(self, aggregate_id: str) -> List[Event]:
        """Get all events for given aggregate."""
        return [e for e in self._events if e.aggregate_id == aggregate_id]
    
    async def close(self) -> None:
        """Close event store."""
        pass

