from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.dependencies import get_command_handler
from app.services.command_handler import CommandHandler

router = APIRouter()

class CreateOrderRequest(BaseModel):
    """Request model for order creation."""
    id: str
    user_id: str
    amount: float

class CancelOrderRequest(BaseModel):
    """Request model for order cancellation."""
    reason: str

@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    handler: CommandHandler = Depends(get_command_handler)
) -> Dict[str, str]:
    """Create new order endpoint."""
    saga_id: str = await handler.handle_create_order(request.model_dump())
    return {"saga_id": saga_id, "order_id": request.id}

@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    handler: CommandHandler = Depends(get_command_handler)
) -> Dict[str, str]:
    """Cancel order endpoint."""
    await handler.handle_cancel_order(order_id, request.reason)
    return {"status": "cancelled", "order_id": order_id}

