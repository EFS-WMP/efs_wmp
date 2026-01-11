import pytest
import pytest_asyncio

from app.core.db import async_session, create_tables
from app.models.bol import BOL, SourceType

HTTP_BLOCK_MESSAGE = "Real HTTP is forbidden in tests; use mocks."


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
            source_type=SourceType.DROP_OFF.value,
        )
        session.add(bol)
        await session.flush()
        yield session
        await session.rollback()


def _is_allowed_httpx_transport(client, httpx_module) -> bool:
    transport = getattr(client, "_transport", None) or getattr(client, "transport", None)
    if transport is None:
        return False
    for name in ("ASGITransport", "MockTransport"):
        transport_cls = getattr(httpx_module, name, None)
        if transport_cls and isinstance(transport, transport_cls):
            return True
    return False


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch, request):
    if request.node.get_closest_marker("allow_real_http"):
        return

    try:
        import requests
    except Exception:
        requests = None

    if requests:
        def _blocked_request(*_args, **_kwargs):
            raise AssertionError(HTTP_BLOCK_MESSAGE)

        monkeypatch.setattr(
            requests.sessions.Session, "request", _blocked_request, raising=True
        )
        monkeypatch.setattr(requests, "request", _blocked_request, raising=True)

    try:
        import httpx
    except Exception:
        httpx = None

    if httpx:
        original_client_request = httpx.Client.request
        original_async_request = httpx.AsyncClient.request

        def _client_request(self, *args, **kwargs):
            if _is_allowed_httpx_transport(self, httpx):
                return original_client_request(self, *args, **kwargs)
            raise AssertionError(HTTP_BLOCK_MESSAGE)

        async def _async_request(self, *args, **kwargs):
            if _is_allowed_httpx_transport(self, httpx):
                return await original_async_request(self, *args, **kwargs)
            raise AssertionError(HTTP_BLOCK_MESSAGE)

        monkeypatch.setattr(httpx.Client, "request", _client_request, raising=True)
        monkeypatch.setattr(httpx.AsyncClient, "request", _async_request, raising=True)
