from typing import Dict, Any, List
from fastapi import APIRouter, Depends
from app.dependencies import get_query_handler
from app.services.query_handler import QueryHandler

router = APIRouter()

@router.get("/orders/{order_id}")
async def get_order(
    order_id: str,
    handler: QueryHandler = Depends(get_query_handler)
) -> Dict[str, Any]:
    """Get order by ID endpoint."""
    return await handler.get_order(order_id)

@router.get("/orders")
async def list_orders(
    user_id: str,
    handler: QueryHandler = Depends(get_query_handler)
) -> List[Dict[str, Any]]:
    """List orders for user endpoint."""
    return await handler.list_orders(user_id)

