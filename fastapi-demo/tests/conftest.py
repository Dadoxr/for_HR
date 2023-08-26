import pytest
import os
import sys
import importlib
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine
import asyncio

from app.core.db import DB
from app.core.models import Base


_test_db = None


@pytest.fixture(scope="function", autouse=True)
def setup_test_db(monkeypatch):
    global _test_db
    
    import tempfile
    test_db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    test_db_file.close()
    test_db_url = f"sqlite+aiosqlite:///{test_db_file.name}"
    
    _test_db = DB(url=test_db_url, echo=False)
    
    from app.order.models import Order
    
    async def create_tables():
        async with _test_db.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    
    asyncio.run(create_tables())
    
    import app.core.db as db_module
    monkeypatch.setattr(db_module, "factory", _test_db)
    
    import app.core as core_module
    if hasattr(core_module, "factory"):
        monkeypatch.setattr(core_module, "factory", _test_db)
    
    modules_to_reload = [
        "app.order.REST.views",
        "app.order.GraphQL.query",
        "app.order.GraphQL.mutation",
        "app.core.urls",
    ]
    for module_name in modules_to_reload:
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
    
    yield
    
    async def cleanup():
        async with _test_db.async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await _test_db.async_engine.dispose()
        if os.path.exists(test_db_file.name):
            os.unlink(test_db_file.name)
    
    asyncio.run(cleanup())


@pytest.fixture
def client(setup_test_db):
    if "main" in sys.modules:
        importlib.reload(sys.modules["main"])
    from main import app
    return TestClient(app)


@pytest.fixture
def test_order_data():
    return {
        "order_id": "test-order-123",
        "user_id": "test-user-456",
        "amount": 99.99
    }

