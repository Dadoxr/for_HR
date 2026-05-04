import strawberry

from app.core.db import get_factory
from ..schemas import OrderOutput, OrderOutputGraphQL
from ..services import OrderService


@strawberry.type
class Query:
    """GraphQL query operations for orders."""

    @strawberry.field
    async def get_all_orders() -> list[OrderOutputGraphQL]:
        """Get all orders."""
        async with get_factory().session_factory() as session:
            orders: list[OrderOutput] = await OrderService.get_all(session=session)
            return [OrderOutputGraphQL.from_output(o) for o in orders]

    @strawberry.field
    async def get_order_by_id(order_id: str) -> OrderOutputGraphQL:
        """Get order by ID."""
        async with get_factory().session_factory() as session:
            order: OrderOutput = await OrderService.get_by_id(
                session=session, order_id=order_id
            )
            return OrderOutputGraphQL.from_output(order)

    @strawberry.field
    async def get_orders_by_user_id(user_id: str) -> list[OrderOutputGraphQL]:
        """Get orders by user ID."""
        async with get_factory().session_factory() as session:
            orders: list[OrderOutput] = await OrderService.get_by_user_id(
                session=session, user_id=user_id
            )
            return [OrderOutputGraphQL.from_output(o) for o in orders]
