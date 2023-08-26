from typing import Dict, Any
from app.services.event_store import EventStore, Event
from app.services.saga_coordinator import SagaCoordinator

class CommandHandler:
    """Handler for command operations in CQRS pattern."""
    
    def __init__(self, event_store: EventStore) -> None:
        self.event_store: EventStore = event_store
        self.saga_coordinator: SagaCoordinator = SagaCoordinator(event_store)
    
    async def handle_create_order(self, order_data: Dict[str, Any]) -> str:
        """Create order command: starts saga and emits OrderCreated event."""
        order_id: str = order_data.get("id")
        
        saga_id: str = await self.saga_coordinator.start_saga("order_creation", {
            "order_id": order_id,
            "user_id": order_data.get("user_id"),
            "amount": order_data.get("amount")
        })
        
        event: Event = Event("OrderCreated", order_id, order_data)
        await self.event_store.append(event)
        
        return saga_id
    
    async def handle_cancel_order(self, order_id: str, reason: str) -> None:
        """Cancel order command: emits OrderCancelled event and compensates saga."""
        event: Event = Event("OrderCancelled", order_id, {"reason": reason})
        await self.event_store.append(event)
        
        await self.saga_coordinator.compensate("order_creation", order_id)

