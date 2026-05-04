import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import commands, queries
from app.core import settings
from app.core.db import get_factory
from app.core.models import Base
from app.core.urls import graphql_app, main_router
from app.dependencies import get_event_store
from app.order.models import Order  # noqa: F401

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize DB and event store on startup."""
    factory = get_factory()
    async with factory.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    await get_event_store().initialize()
    try:
        yield
    finally:
        await get_event_store().close()
        await factory.engine.dispose()
        logger.info("Application shutdown complete")


app = FastAPI(title="Production API", lifespan=lifespan, debug=settings.DEBUG)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello World"}


app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
app.include_router(queries.router, prefix="/api/v1", tags=["queries"])
app.include_router(router=main_router.rest)
app.include_router(router=graphql_app)
