from typing import Dict, Any, AsyncGenerator
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.dependencies import get_event_store
from app.api import commands, queries
from app.core import settings
from app.core.urls import main_router, graphql_app
from app.core.db import factory
from app.core.models import Base
from app.order.models import Order

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize DB and event store on startup."""
    async with factory.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await get_event_store().initialize()
    yield
    await get_event_store().close()

app = FastAPI(title="Production API", lifespan=lifespan, debug=settings.DEBUG)

@app.get("/health")
async def health() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {"message": "Hello World"}

app.include_router(commands.router, prefix="/api/v1", tags=["commands"])
app.include_router(queries.router, prefix="/api/v1", tags=["queries"])
app.include_router(router=main_router.rest)
app.include_router(router=graphql_app)

