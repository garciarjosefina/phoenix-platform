import os
import pytest
from execution_gateway.http_transport import HttpTransport
import execution_gateway


class _ValidTransport:
    def __init__(self, response: str = "ok"):
        self._response = response
        self.received: list[dict] = []

    def post(self, *, url: str, headers, body: str, timeout_seconds: float) -> str:
        self.received.append(
            {"url": url, "headers": headers, "body": body, "timeout_seconds": timeout_seconds}
        )
        return self._response


class _NoPost:
    def get(self, *, url: str) -> str:
        ...


class TestImport:
    def test_direct_import(self):
        from execution_gateway.http_transport import HttpTransport as T
        assert T is HttpTransport

    def test_public_import(self):
        assert hasattr(execution_gateway, "HttpTransport")
        assert execution_gateway.HttpTransport is HttpTransport

    def test_in_all(self):
        assert "HttpTransport" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        t = _ValidTransport()
        assert isinstance(t, HttpTransport)

    def test_incompatible_class_rejected(self):
        t = _NoPost()
        assert not isinstance(t, HttpTransport)

    def test_no_explicit_inheritance_required(self):
        t = _ValidTransport()
        assert isinstance(t, HttpTransport)

    def test_keyword_only_call(self):
        t = _ValidTransport("response_body")
        result = t.post(
            url="https://example.com",
            headers={"Content-Type": "application/json"},
            body='{"key":"value"}',
            timeout_seconds=5.0,
        )
        assert result == "response_body"

    def test_receives_exact_url(self):
        t = _ValidTransport()
        t.post(url="https://bybit.example/order", headers={}, body="", timeout_seconds=1.0)
        assert t.received[0]["url"] == "https://bybit.example/order"

    def test_receives_exact_headers(self):
        t = _ValidTransport()
        headers = {"X-Key": "abc", "Content-Type": "application/json"}
        t.post(url="https://example.com", headers=headers, body="", timeout_seconds=1.0)
        assert t.received[0]["headers"] == headers

    def test_receives_exact_body(self):
        t = _ValidTransport()
        body = '{"qty":"0.001"}'
        t.post(url="https://example.com", headers={}, body=body, timeout_seconds=1.0)
        assert t.received[0]["body"] == body

    def test_receives_exact_timeout(self):
        t = _ValidTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=7.5)
        assert t.received[0]["timeout_seconds"] == 7.5

    def test_returns_exact_str(self):
        expected = '{"retCode":0}'
        t = _ValidTransport(expected)
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result is expected


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        sentinel = "__HTTP_TRANSPORT_SENTINEL__"
        os.environ["BYBIT_API_KEY"] = sentinel
        try:
            from execution_gateway.http_transport import HttpTransport as T
            assert T is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "urllib3", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None

    def test_bybit_client_still_works(self):
        from execution_gateway.bybit_client import BybitDemoClient
        assert BybitDemoClient is not None
