import strawberry

from app.core.db import get_factory
from ..schemas import (
    OrderCreateInput,
    OrderCreateInputGraphQL,
    OrderOutput,
    OrderOutputGraphQL,
    OrderUpdateInput,
    OrderUpdateInputGraphQL,
)
from ..services import OrderService


@strawberry.type
class Mutation:
    """GraphQL mutation operations for orders."""

    @strawberry.field
    async def create_order(order: OrderCreateInputGraphQL) -> OrderOutputGraphQL:
        """Create new order."""
        async with get_factory().session_factory() as session:
            order_input = OrderCreateInput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount,
            )
            result: OrderOutput = await OrderService.create(
                session=session, order_create=order_input
            )
            return OrderOutputGraphQL.from_output(result)

    @strawberry.field
    async def update_order(
        order_id: str, order_update: OrderUpdateInputGraphQL
    ) -> OrderOutputGraphQL:
        """Update order."""
        async with get_factory().session_factory() as session:
            update_input = OrderUpdateInput(status=order_update.status)
            result: OrderOutput = await OrderService.update(
                session=session, order_id=order_id, order_update=update_input
            )
            return OrderOutputGraphQL.from_output(result)

    @strawberry.field
    async def delete_order(order_id: str) -> None:
        """Delete order."""
        async with get_factory().session_factory() as session:
            await OrderService.delete(session=session, order_id=order_id)
