import logging
from typing import Any

from app.services.event_store import Event, EventStore

logger = logging.getLogger(__name__)


class SagaCoordinator:
    """Coordinator for distributed transactions using Saga pattern.

    In-memory implementation for demonstration. In production,
    saga state would be persisted to a database.
    """

    def __init__(self, event_store: EventStore) -> None:
        self.event_store = event_store
        self._sagas: dict[str, dict[str, Any]] = {}

    async def start_saga(self, saga_type: str, data: dict[str, Any]) -> str:
        """Start saga transaction: execute steps sequentially."""
        saga_id = f"{saga_type}_{data.get('order_id')}"

        self._sagas[saga_id] = {
            "type": saga_type,
            "status": "started",
            "steps": [],
            "data": data,
        }

        await self._execute_step(saga_id, "reserve_inventory", data)
        await self._execute_step(saga_id, "charge_payment", data)

        self._sagas[saga_id]["status"] = "completed"
        logger.info("Saga %s completed", saga_id)
        return saga_id

    async def _execute_step(
        self, saga_id: str, step: str, data: dict[str, Any]
    ) -> None:
        """Execute single saga step and record event."""
        event = Event("SagaStepExecuted", saga_id, {"step": step, "data": data})
        await self.event_store.append(event)
        self._sagas[saga_id]["steps"].append(step)

    async def compensate(self, saga_type: str, aggregate_id: str) -> None:
        """Compensate saga: rollback steps in reverse order."""
        saga_id = f"{saga_type}_{aggregate_id}"
        if saga_id in self._sagas:
            for step in reversed(self._sagas[saga_id]["steps"]):
                await self._compensate_step(saga_id, step)
            self._sagas[saga_id]["status"] = "compensated"
            logger.info("Saga %s compensated", saga_id)

    async def _compensate_step(self, saga_id: str, step: str) -> None:
        """Compensate single saga step."""
        event = Event("SagaStepCompensated", saga_id, {"step": step})
        await self.event_store.append(event)
