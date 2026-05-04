import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

logger = logging.getLogger(__name__)


class DB:
    def __init__(self, url: str, echo: bool = False) -> None:
        self.engine = create_async_engine(url=url, echo=echo)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )


_factory: DB | None = None


def get_factory() -> DB:
    """Get the global DB factory. Lazily initializes on first call."""
    global _factory
    if _factory is None:
        _factory = DB(url=settings.db_url, echo=settings.db_echo)
    return _factory


def set_factory(factory: DB) -> None:
    """Override the global DB factory (used in tests)."""
    global _factory
    _factory = factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yields a database session per request."""
    factory = get_factory()
    async with factory.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
