from typing import Dict, Any, List
from app.services.event_store import EventStore, Event

class QueryHandler:
    """Handler for query operations in CQRS pattern."""
    
    def __init__(self, event_store: EventStore) -> None:
        self.event_store: EventStore = event_store
        self._cache: Dict[str, Dict[str, Any]] = {}
    
    async def get_order(self, order_id: str) -> Dict[str, Any]:
        """Get order by replaying events from event store."""
        events: List[Event] = await self.event_store.get_events(order_id)
        
        state: Dict[str, Any] = {"id": order_id, "status": "pending"}
        for event in events:
            if event.event_type == "OrderCreated":
                state.update(event.data)
                state["status"] = "created"
            elif event.event_type == "OrderCancelled":
                state["status"] = "cancelled"
                state["cancel_reason"] = event.data.get("reason")
        
        return state
    
    async def list_orders(self, user_id: str) -> List[Dict[str, Any]]:
        """List orders for given user."""
        return []

