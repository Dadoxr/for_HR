from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import strawberry
from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .models import Order


class OrderOutput(BaseModel):
    order_id: str
    user_id: str
    amount: Decimal
    status: str

    @classmethod
    def from_model(cls, order: Order) -> OrderOutput:
        return cls(
            order_id=order.order_id,
            user_id=order.user_id,
            amount=order.amount,
            status=order.status,
        )


class OrderCreateInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    user_id: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)


class OrderUpdateInput(BaseModel):
    status: str | None = None


@strawberry.type
class OrderOutputGraphQL:
    order_id: str
    user_id: str
    amount: float
    status: str

    @classmethod
    def from_output(cls, output: OrderOutput) -> OrderOutputGraphQL:
        return cls(
            order_id=output.order_id,
            user_id=output.user_id,
            amount=float(output.amount),
            status=output.status,
        )


@strawberry.input
class OrderCreateInputGraphQL:
    order_id: str
    user_id: str
    amount: float


@strawberry.input
class OrderUpdateInputGraphQL:
    status: str | None = None
