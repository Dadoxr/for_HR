import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order
from .schemas import OrderUpdateInput

logger = logging.getLogger(__name__)


class OrderDAL:
    """Data Access Layer for Order model."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[Order]:
        stmt = select(Order)
        result = await session.scalars(stmt)
        return list(result.all())

    @staticmethod
    async def get_by_id(session: AsyncSession, order_id: str) -> Order | None:
        stmt = select(Order).where(Order.order_id == order_id)
        return await session.scalar(stmt)

    @staticmethod
    async def get_by_user_id(session: AsyncSession, user_id: str) -> list[Order]:
        stmt = select(Order).where(Order.user_id == user_id)
        result = await session.scalars(stmt)
        return list(result.all())

    @staticmethod
    async def create(session: AsyncSession, order: Order) -> Order:
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def update(
        session: AsyncSession,
        order: Order,
        order_update: OrderUpdateInput,
    ) -> Order:
        if order_update.status:
            order.status = order_update.status
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def delete(session: AsyncSession, order: Order) -> None:
        await session.delete(order)
        await session.commit()
