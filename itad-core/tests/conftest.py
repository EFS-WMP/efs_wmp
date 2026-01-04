import pytest_asyncio

from app.core.db import async_session, create_tables
from app.models.bol import BOL


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_schema():
    await create_tables()


@pytest_asyncio.fixture
async def db_session():
    await create_tables()
    async with async_session() as session:
        bol = BOL(
            id="bol-123",
            bol_number="bol-123",
            customer_snapshot_json={"name": "demo"},
        )
        session.add(bol)
        await session.flush()
        yield session
        await session.rollback()
