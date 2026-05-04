import logging
from typing import Any

from app.services.event_store import Event, EventStore
from app.services.saga_coordinator import SagaCoordinator

logger = logging.getLogger(__name__)


class CommandHandler:
    """Handler for command operations in CQRS pattern."""

    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store
        self.saga_coordinator = SagaCoordinator(event_store)

    async def handle_create_order(self, order_data: dict[str, Any]) -> str:
        """Create order command: starts saga and emits OrderCreated event."""
        order_id: str = order_data.get("id")

        saga_id = await self.saga_coordinator.start_saga(
            "order_creation",
            {
                "order_id": order_id,
                "user_id": order_data.get("user_id"),
                "amount": order_data.get("amount"),
            },
        )

        event = Event("OrderCreated", order_id, order_data)
        await self.event_store.append(event)
        logger.info("Order %s created via CQRS", order_id)

        return saga_id

    async def handle_cancel_order(self, order_id: str, reason: str) -> None:
        """Cancel order command: emits OrderCancelled event and compensates saga."""
        event = Event("OrderCancelled", order_id, {"reason": reason})
        await self.event_store.append(event)

        await self.saga_coordinator.compensate("order_creation", order_id)
        logger.info("Order %s cancelled", order_id)
