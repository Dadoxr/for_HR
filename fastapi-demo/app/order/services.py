import logging

from sqlalchemy.ext.asyncio import AsyncSession

from .dals import OrderDAL
from .exceptions import OrderNotFoundError
from .models import Order
from .schemas import OrderCreateInput, OrderOutput, OrderUpdateInput

logger = logging.getLogger(__name__)


class OrderService:
    """Service layer for order business logic."""

    @staticmethod
    async def get_all(session: AsyncSession) -> list[OrderOutput]:
        orders = await OrderDAL.get_all(session=session)
        return [OrderOutput.from_model(order) for order in orders]

    @staticmethod
    async def get_by_id(session: AsyncSession, order_id: str) -> OrderOutput:
        order = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            return OrderOutput.from_model(order)
        raise OrderNotFoundError(order_id)

    @staticmethod
    async def get_by_user_id(session: AsyncSession, user_id: str) -> list[OrderOutput]:
        orders = await OrderDAL.get_by_user_id(session=session, user_id=user_id)
        return [OrderOutput.from_model(order) for order in orders]

    @staticmethod
    async def create(session: AsyncSession, order_create: OrderCreateInput) -> OrderOutput:
        order = Order(
            order_id=order_create.order_id,
            user_id=order_create.user_id,
            amount=order_create.amount,
            status="pending",
        )
        order = await OrderDAL.create(order=order, session=session)
        return OrderOutput.from_model(order)

    @staticmethod
    async def update(
        session: AsyncSession,
        order_id: str,
        order_update: OrderUpdateInput,
    ) -> OrderOutput:
        order = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            order = await OrderDAL.update(
                session=session, order=order, order_update=order_update
            )
            return OrderOutput.from_model(order)
        raise OrderNotFoundError(order_id)

    @staticmethod
    async def delete(session: AsyncSession, order_id: str) -> None:
        order = await OrderDAL.get_by_id(session=session, order_id=order_id)
        if order:
            await OrderDAL.delete(session=session, order=order)
            return
        raise OrderNotFoundError(order_id)
