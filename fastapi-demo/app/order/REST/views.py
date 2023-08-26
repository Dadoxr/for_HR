from typing import List
from fastapi import APIRouter, status

from ...core import factory
from ..schemas import OrderOutput, OrderCreateInput, OrderUpdateInput
from ..services import OrderService

router = APIRouter(prefix="/orders")


@router.get("/all", response_model=List[OrderOutput], status_code=status.HTTP_200_OK)
async def get_all() -> List[OrderOutput]:
    """Get all orders."""
    async with factory.get_session() as session:
        return await OrderService.get_all(session=session)


@router.get("/{order_id}", response_model=OrderOutput, status_code=status.HTTP_200_OK)
async def get_by_id(order_id: str) -> OrderOutput:
    """Get order by ID."""
    async with factory.get_session() as session:
        return await OrderService.get_by_id(session=session, order_id=order_id)


@router.get("/", response_model=List[OrderOutput], status_code=status.HTTP_200_OK)
async def get_by_user_id(user_id: str) -> List[OrderOutput]:
    """Get orders by user ID."""
    async with factory.get_session() as session:
        return await OrderService.get_by_user_id(session=session, user_id=user_id)


@router.post("/", response_model=OrderOutput, status_code=status.HTTP_201_CREATED)
async def create(order: OrderCreateInput) -> OrderOutput:
    """Create new order."""
    async with factory.get_session() as session:
        return await OrderService.create(session=session, order_create=order)


@router.patch("/{order_id}", response_model=OrderOutput, status_code=status.HTTP_200_OK)
async def update(order_id: str, order_update: OrderUpdateInput) -> OrderOutput:
    """Update order."""
    async with factory.get_session() as session:
        return await OrderService.update(session=session, order_id=order_id, order_update=order_update)


@router.delete("/{order_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete(order_id: str) -> None:
    """Delete order."""
    async with factory.get_session() as session:
        await OrderService.delete(session=session, order_id=order_id)

