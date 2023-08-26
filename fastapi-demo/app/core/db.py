import asyncio
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_scoped_session
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings


class DB:
    def __init__(self, url: str, echo: bool = False) -> None:
        self.async_engine = create_async_engine(url=url, echo=echo)
        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def get_scope_session(self) -> AsyncSession:
        scope = async_scoped_session(
            session_factory=self.async_session_factory,
            scopefunc=asyncio.current_task,
        )
        return scope

    @asynccontextmanager
    async def get_session(self):
        session = self.get_scope_session()
        try:
            yield session
        finally:
            await session.remove()


factory = DB(url=settings.db_url, echo=settings.db_echo)

