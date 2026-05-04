import logging
from typing import Any

from app.services.event_store import Event, EventStore

logger = logging.getLogger(__name__)


class QueryHandler:
    """Handler for query operations in CQRS pattern."""

    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store

    async def get_order(self, order_id: str) -> dict[str, Any]:
        """Get order by replaying events from event store."""
        events: list[Event] = await self.event_store.get_events(order_id)

        state: dict[str, Any] = {"id": order_id, "status": "pending"}
        for event in events:
            if event.event_type == "OrderCreated":
                state.update(
                    {k: v for k, v in event.data.items() if k != "status"}
                )
                state["status"] = "created"
            elif event.event_type == "OrderCancelled":
                state["status"] = "cancelled"
                state["cancel_reason"] = event.data.get("reason")

        return state

    async def list_orders(self, user_id: str) -> list[dict[str, Any]]:
        """List orders for given user by replaying events."""
        aggregate_ids = await self.event_store.get_all_aggregate_ids()
        orders = []
        for order_id in aggregate_ids:
            state = await self.get_order(order_id)
            if state.get("user_id") == user_id:
                orders.append(state)
        return orders
