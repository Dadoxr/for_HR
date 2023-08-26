from typing import Dict, Any
from app.services.event_store import EventStore, Event

class SagaCoordinator:
    """Coordinator for distributed transactions using Saga pattern."""
    
    def __init__(self, event_store: EventStore) -> None:
        self.event_store: EventStore = event_store
        self._sagas: Dict[str, Dict[str, Any]] = {}
    
    async def start_saga(self, saga_type: str, data: Dict[str, Any]) -> str:
        """Start saga transaction: execute steps sequentially."""
        saga_id: str = f"{saga_type}_{data.get('order_id')}"
        
        self._sagas[saga_id] = {
            "type": saga_type,
            "status": "started",
            "steps": [],
            "data": data
        }
        
        await self._execute_step(saga_id, "reserve_inventory", data)
        await self._execute_step(saga_id, "charge_payment", data)
        
        self._sagas[saga_id]["status"] = "completed"
        return saga_id
    
    async def _execute_step(self, saga_id: str, step: str, data: Dict[str, Any]) -> None:
        """Execute single saga step and record event."""
        event: Event = Event("SagaStepExecuted", saga_id, {"step": step, "data": data})
        await self.event_store.append(event)
        self._sagas[saga_id]["steps"].append(step)
    
    async def compensate(self, saga_type: str, aggregate_id: str) -> None:
        """Compensate saga: rollback steps in reverse order."""
        saga_id: str = f"{saga_type}_{aggregate_id}"
        if saga_id in self._sagas:
            for step in reversed(self._sagas[saga_id]["steps"]):
                await self._compensate_step(saga_id, step)
            self._sagas[saga_id]["status"] = "compensated"
    
    async def _compensate_step(self, saga_id: str, step: str) -> None:
        """Compensate single saga step."""
        event: Event = Event("SagaStepCompensated", saga_id, {"step": step})
        await self.event_store.append(event)

