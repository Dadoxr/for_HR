from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from ..exceptions import OrderNotFoundError
from ..schemas import OrderCreateInput, OrderOutput, OrderUpdateInput
from ..services import OrderService

router = APIRouter(prefix="/orders")


@router.get("/all", response_model=list[OrderOutput], status_code=status.HTTP_200_OK)
async def get_all(session: AsyncSession = Depends(get_session)) -> list[OrderOutput]:
    """Get all orders."""
    return await OrderService.get_all(session=session)


@router.get("/{order_id}", response_model=OrderOutput, status_code=status.HTTP_200_OK)
async def get_by_id(
    order_id: str, session: AsyncSession = Depends(get_session)
) -> OrderOutput:
    """Get order by ID."""
    try:
        return await OrderService.get_by_id(session=session, order_id=order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )


@router.get("/", response_model=list[OrderOutput], status_code=status.HTTP_200_OK)
async def get_by_user_id(
    user_id: str, session: AsyncSession = Depends(get_session)
) -> list[OrderOutput]:
    """Get orders by user ID."""
    return await OrderService.get_by_user_id(session=session, user_id=user_id)


@router.post("/", response_model=OrderOutput, status_code=status.HTTP_201_CREATED)
async def create(
    order: OrderCreateInput, session: AsyncSession = Depends(get_session)
) -> OrderOutput:
    """Create new order."""
    return await OrderService.create(session=session, order_create=order)


@router.patch("/{order_id}", response_model=OrderOutput, status_code=status.HTTP_200_OK)
async def update(
    order_id: str,
    order_update: OrderUpdateInput,
    session: AsyncSession = Depends(get_session),
) -> OrderOutput:
    """Update order."""
    try:
        return await OrderService.update(
            session=session, order_id=order_id, order_update=order_update
        )
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )


@router.delete("/{order_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def delete(
    order_id: str, session: AsyncSession = Depends(get_session)
) -> None:
    """Delete order."""
    try:
        await OrderService.delete(session=session, order_id=order_id)
    except OrderNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found",
        )
