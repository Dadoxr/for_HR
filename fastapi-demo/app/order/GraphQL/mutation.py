import strawberry

from ...core import factory
from ..schemas import OrderOutputGraphQL, OrderCreateInputGraphQL, OrderUpdateInputGraphQL
from ..services import OrderService
from ..schemas import OrderCreateInput, OrderUpdateInput, OrderOutput


@strawberry.type
class Mutation:
    """GraphQL mutation operations for orders."""

    @strawberry.field
    async def create_order(order: OrderCreateInputGraphQL) -> OrderOutputGraphQL:
        """Create new order."""
        async with factory.get_session() as session:
            order_input: OrderCreateInput = OrderCreateInput(
                order_id=order.order_id,
                user_id=order.user_id,
                amount=order.amount
            )
            result: OrderOutput = await OrderService.create(session=session, order_create=order_input)
            return OrderOutputGraphQL(
                order_id=result.order_id,
                user_id=result.user_id,
                amount=result.amount,
                status=result.status
            )

    @strawberry.field
    async def update_order(
        order_id: str, order_update: OrderUpdateInputGraphQL
    ) -> OrderOutputGraphQL:
        """Update order."""
        async with factory.get_session() as session:
            update_input: OrderUpdateInput = OrderUpdateInput(status=order_update.status)
            result: OrderOutput = await OrderService.update(
                session=session, order_id=order_id, order_update=update_input
            )
            return OrderOutputGraphQL(
                order_id=result.order_id,
                user_id=result.user_id,
                amount=result.amount,
                status=result.status
            )

    @strawberry.field
    async def delete_order(order_id: str) -> None:
        """Delete order."""
        async with factory.get_session() as session:
            await OrderService.delete(session=session, order_id=order_id)

