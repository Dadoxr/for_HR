from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.storage.models import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="LLM RAG Demo",
    description="RAG pipeline with multi-provider LLM fallback",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(router)
