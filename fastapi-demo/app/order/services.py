from typing import List
from fastapi import HTTPException
from fastapi import status
from sqlalchemy.ext.asyncio import AsyncSession

from .dals import OrderDAL
from .schemas import OrderOutput, OrderCreateInput, OrderUpdateInput
from .models import Order


class OrderService:
    """Service layer for order business logic."""
    
    @staticmethod
    async def get_all(session: AsyncSession) -> List[OrderOutput]:
        """Get all orders."""
        orders: List[Order] = await OrderDAL.get_all(session=session)
        return [
            OrderOutput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
                status=order.status
            ) for order in orders
        ]

    @staticmethod
    async def get_by_id(
        session: AsyncSession, order_id: str
    ) -> OrderOutput:
        """Get order by ID or raise 404."""
        order: Order | None = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            return OrderOutput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
                status=order.status
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found!",
        )

    @staticmethod
    async def get_by_user_id(
        session: AsyncSession, user_id: str
    ) -> List[OrderOutput]:
        """Get all orders for given user."""
        orders: List[Order] = await OrderDAL.get_by_user_id(session=session, user_id=user_id)
        return [
            OrderOutput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
                status=order.status
            ) for order in orders
        ]

    @staticmethod
    async def create(session: AsyncSession, order_create: OrderCreateInput) -> OrderOutput:
        """Create new order."""
        order: Order = Order(
            order_id=order_create.order_id,
            user_id=order_create.user_id,
            amount=order_create.amount,
            status="pending"
        )
        order = await OrderDAL.create(order=order, session=session)
        return OrderOutput(
            order_id=order.order_id,
            user_id=order.user_id,
            amount=order.amount,
            status=order.status
        )

    @staticmethod
    async def update(
        session: AsyncSession,
        order_id: str,
        order_update: OrderUpdateInput,
    ) -> OrderOutput:
        """Update order or raise 404."""
        order: Order | None = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            order = await OrderDAL.update(
                session=session, order=order, order_update=order_update
            )
            return OrderOutput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
                status=order.status
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found!",
        )

    @staticmethod
    async def delete(session: AsyncSession, order_id: str) -> None:
        """Delete order or raise 404."""
        order: Order | None = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            await OrderDAL.delete(session=session, order=order)
            return
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order {order_id} not found!",
        )

