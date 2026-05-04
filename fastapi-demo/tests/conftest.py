import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.db import DB, get_session, set_factory
from app.core.models import Base


@pytest.fixture(scope="function")
async def test_db():
    """Create a fresh test database for each test."""
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()
    url = f"sqlite+aiosqlite:///{tmp.name}"

    test_factory = DB(url=url, echo=False)

    from app.order.models import Order  # noqa: F401

    async with test_factory.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Override global factory so both REST (via get_session) and GraphQL use test DB
    set_factory(test_factory)

    yield test_factory

    async with test_factory.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_factory.engine.dispose()
    set_factory(None)

    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture(scope="function")
async def client(test_db):
    """Async test client with overridden DB session."""
    from main import app

    async def override_get_session():
        async with test_db.session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test", follow_redirects=True
        ) as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def test_order_data():
    return {
        "order_id": "test-order-123",
        "user_id": "test-user-456",
        "amount": 99.99,
    }
