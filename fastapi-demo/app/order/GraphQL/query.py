from typing import List
import strawberry

from ..services import OrderService
from ...core import factory
from ..schemas import OrderOutputGraphQL, OrderOutput


@strawberry.type
class Query:
    """GraphQL query operations for orders."""

    @strawberry.field
    async def get_all_orders() -> List[OrderOutputGraphQL]:
        """Get all orders."""
        async with factory.get_session() as session:
            orders: List[OrderOutput] = await OrderService.get_all(session=session)
            return [
                OrderOutputGraphQL(
                    order_id=o.order_id,
                    user_id=o.user_id,
                    amount=o.amount,
                    status=o.status
                )
                for o in orders
            ]

    @strawberry.field
    async def get_order_by_id(order_id: str) -> OrderOutputGraphQL:
        """Get order by ID."""
        async with factory.get_session() as session:
            order: OrderOutput = await OrderService.get_by_id(session=session, order_id=order_id)
            return OrderOutputGraphQL(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
                status=order.status
            )

    @strawberry.field
    async def get_orders_by_user_id(user_id: str) -> List[OrderOutputGraphQL]:
        """Get orders by user ID."""
        async with factory.get_session() as session:
            orders: List[OrderOutput] = await OrderService.get_by_user_id(session=session, user_id=user_id)
            return [
                OrderOutputGraphQL(
                    order_id=o.order_id,
                    user_id=o.user_id,
                    amount=o.amount,
                    status=o.status
                )
                for o in orders
            ]

