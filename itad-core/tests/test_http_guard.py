import httpx
import pytest


class _DummyClient:
    _transport = None


def test_real_http_is_blocked_by_default():
    with pytest.raises(AssertionError, match="Real HTTP is forbidden in tests; use mocks."):
        httpx.Client.request(_DummyClient(), "GET", "http://example.com")
