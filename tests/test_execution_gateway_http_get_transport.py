import execution_gateway
from execution_gateway.http_get_transport import HttpGetTransport


class _ValidTransport:
    def __init__(self, response: str = "ok"):
        self._response = response
        self.received: list[dict] = []

    def get(self, *, url: str, headers, timeout_seconds: float) -> str:
        self.received.append({"url": url, "headers": headers, "timeout_seconds": timeout_seconds})
        return self._response


class _NoGet:
    def post(self, *, url: str) -> str:
        ...


class TestImport:
    def test_direct_import(self):
        from execution_gateway.http_get_transport import HttpGetTransport as T
        assert T is HttpGetTransport

    def test_public_import(self):
        assert hasattr(execution_gateway, "HttpGetTransport")
        assert execution_gateway.HttpGetTransport is HttpGetTransport

    def test_in_all(self):
        assert "HttpGetTransport" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidTransport(), HttpGetTransport)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoGet(), HttpGetTransport)

    def test_post_only_transport_is_not_a_get_transport(self):
        # HttpTransport (post) y HttpGetTransport (get) son Protocols
        # distintos y no intercambiables -- no se reutilizó/mutó el
        # contrato existente.
        from execution_gateway.urllib_http_transport import UrllibHttpTransport
        assert not isinstance(UrllibHttpTransport(), HttpGetTransport)

    def test_keyword_only_call(self):
        t = _ValidTransport("response_body")
        result = t.get(url="https://example.com", headers={}, timeout_seconds=5.0)
        assert result == "response_body"

    def test_receives_exact_url_headers_timeout(self):
        t = _ValidTransport()
        headers = {"X-BAPI-API-KEY": "abc"}
        t.get(url="https://bybit.example/v5/position/list?category=linear", headers=headers, timeout_seconds=7.5)
        assert t.received[0]["url"] == "https://bybit.example/v5/position/list?category=linear"
        assert t.received[0]["headers"] == headers
        assert t.received[0]["timeout_seconds"] == 7.5


class TestExistingSuiteUnaffected:
    def test_http_transport_protocol_still_only_has_post(self):
        from execution_gateway.http_transport import HttpTransport
        assert not hasattr(HttpTransport, "get")
