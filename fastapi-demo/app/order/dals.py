from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import Result

from .models import Order
from .schemas import OrderCreateInput, OrderUpdateInput


class OrderDAL:
    """Data Access Layer for Order model."""
    
    @staticmethod
    async def get_all(session: AsyncSession) -> List[Order]:
        """Get all orders."""
        stmp = select(Order)
        result: Result = await session.scalars(stmp)
        return list(result.all())

    @staticmethod
    async def get_by_id(session: AsyncSession, order_id: str) -> Order | None:
        """Get order by ID."""
        stmp = select(Order).where(Order.order_id == order_id)
        return await session.scalar(stmp)

    @staticmethod
    async def get_by_user_id(session: AsyncSession, user_id: str) -> List[Order]:
        """Get all orders for given user."""
        stmp = select(Order).where(Order.user_id == user_id)
        result: Result = await session.scalars(stmp)
        return list(result.all())

    @staticmethod
    async def create(session: AsyncSession, order: Order) -> Order:
        """Create new order."""
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def update(
        session: AsyncSession,
        order: Order,
        order_update: OrderUpdateInput,
    ) -> Order | None:
        """Update order."""
        if order_update.status:
            order.status = order_update.status
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def delete(session: AsyncSession, order: Order) -> None:
        """Delete order."""
        await session.delete(order)
        await session.commit()

