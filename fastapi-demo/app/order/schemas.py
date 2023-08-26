from pydantic import BaseModel
import strawberry


class OrderOutput(BaseModel):
    order_id: str
    user_id: str
    amount: float
    status: str


class OrderCreateInput(BaseModel):
    order_id: str
    user_id: str
    amount: float


class OrderUpdateInput(BaseModel):
    status: str | None = None


@strawberry.type
class OrderOutputGraphQL:
    order_id: str
    user_id: str
    amount: float
    status: str


@strawberry.input
class OrderCreateInputGraphQL:
    order_id: str
    user_id: str
    amount: float


@strawberry.input
class OrderUpdateInputGraphQL:
    status: str | None = None

