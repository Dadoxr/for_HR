from sqlalchemy import String, Float
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from app.core import Base


class Order(Base):
    order_id: Mapped[str] = mapped_column(String(100), unique=True)
    user_id: Mapped[str] = mapped_column(String(100))
    amount: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(50), default="pending")

