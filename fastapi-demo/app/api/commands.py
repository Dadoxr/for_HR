from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.dependencies import get_command_handler
from app.services.command_handler import CommandHandler

router = APIRouter()


class CreateOrderRequest(BaseModel):
    """Request model for order creation."""

    id: str = Field(min_length=1)
    user_id: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)


class CancelOrderRequest(BaseModel):
    """Request model for order cancellation."""

    reason: str = Field(min_length=1)


@router.post("/orders", status_code=201)
async def create_order(
    request: CreateOrderRequest,
    handler: CommandHandler = Depends(get_command_handler),
) -> dict[str, str]:
    """Create new order endpoint."""
    saga_id = await handler.handle_create_order(request.model_dump())
    return {"saga_id": saga_id, "order_id": request.id}


@router.post("/orders/{order_id}/cancel")
async def cancel_order(
    order_id: str,
    request: CancelOrderRequest,
    handler: CommandHandler = Depends(get_command_handler),
) -> dict[str, str]:
    """Cancel order endpoint."""
    await handler.handle_cancel_order(order_id, request.reason)
    return {"status": "cancelled", "order_id": order_id}
