import os
import pytest
import execution_gateway
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.bybit_endpoint import BybitEndpoint


# ── helpers ────────────────────────────────────────────────────────────────

def _make_builder(base_url: str = "https://example.com") -> BybitUrlBuilder:
    return BybitUrlBuilder(base_url=base_url)


def _ep(method: str = "GET", path: str = "/v5/order/realtime") -> BybitEndpoint:
    return BybitEndpoint(method=method, path=path)


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_url_builder import BybitUrlBuilder as B
        assert B is BybitUrlBuilder

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitUrlBuilder")
        assert execution_gateway.BybitUrlBuilder is BybitUrlBuilder

    def test_in_all(self):
        assert "BybitUrlBuilder" in execution_gateway.__all__

    def test_valid_construction(self):
        b = _make_builder()
        assert b is not None


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_preserves_base_url_exactly(self):
        url = "https://api-demo.bybit.com"
        b = BybitUrlBuilder(base_url=url)
        assert b._base_url is url

    def test_rejects_non_str_base_url(self):
        with pytest.raises(TypeError):
            BybitUrlBuilder(base_url=123)

    def test_rejects_none_base_url(self):
        with pytest.raises(TypeError):
            BybitUrlBuilder(base_url=None)

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="")

    def test_rejects_whitespace_string(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="   ")

    def test_rejects_no_scheme(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="api-demo.bybit.com")

    def test_rejects_http(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="http://api-demo.bybit.com")

    def test_rejects_https_without_host(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="https://")

    def test_rejects_trailing_slash(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="https://api-demo.bybit.com/")

    def test_rejects_path_in_base_url(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="https://api-demo.bybit.com/v5")

    def test_rejects_query_string(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="https://api-demo.bybit.com?x=1")

    def test_rejects_fragment(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="https://api-demo.bybit.com#fragment")

    def test_accepts_port(self):
        b = BybitUrlBuilder(base_url="https://example.com:443")
        assert b._base_url == "https://example.com:443"

    def test_accepts_subdomain(self):
        b = BybitUrlBuilder(base_url="https://subdomain.example.com")
        assert b._base_url == "https://subdomain.example.com"

    def test_no_normalization_uppercase_scheme(self):
        with pytest.raises(ValueError):
            BybitUrlBuilder(base_url="HTTPS://example.com")

    def test_no_network_call(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        _make_builder()
        assert called == []

    def test_no_env_read(self):
        os.environ["BYBIT_BASE_URL"] = "__sentinel__"
        try:
            b = _make_builder()
            assert b is not None
        finally:
            del os.environ["BYBIT_BASE_URL"]


# ── build ──────────────────────────────────────────────────────────────────

class TestBuild:
    def test_endpoint_must_be_keyword_only(self):
        b = _make_builder()
        ep = _ep()
        with pytest.raises(TypeError):
            b.build(ep)

    def test_rejects_incompatible_endpoint(self):
        b = _make_builder()
        with pytest.raises(TypeError):
            b.build(endpoint=object())

    def test_rejects_none_endpoint(self):
        b = _make_builder()
        with pytest.raises(TypeError):
            b.build(endpoint=None)

    def test_accepts_get_endpoint(self):
        b = _make_builder()
        ep = _ep(method="GET", path="/v5/order/realtime")
        result = b.build(endpoint=ep)
        assert isinstance(result, str)

    def test_accepts_post_endpoint(self):
        b = _make_builder()
        ep = _ep(method="POST", path="/v5/order/create")
        result = b.build(endpoint=ep)
        assert isinstance(result, str)

    def test_concatenates_simple_path(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(path="/v5/order/realtime")
        assert b.build(endpoint=ep) == "https://example.com/v5/order/realtime"

    def test_concatenates_multiple_segments(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(path="/v5/order/cancel")
        assert b.build(endpoint=ep) == "https://example.com/v5/order/cancel"

    def test_concatenates_path_with_query_string(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(path="/v5/order/realtime?category=linear")
        assert b.build(endpoint=ep) == "https://example.com/v5/order/realtime?category=linear"

    def test_preserves_query_string_exactly(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        qs = "/v5/order/realtime?category=linear&symbol=BTCUSDT"
        ep = _ep(path=qs)
        assert b.build(endpoint=ep) == "https://example.com" + qs

    def test_preserves_characters_exactly(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        path = "/v5/position/list"
        ep = _ep(path=path)
        assert b.build(endpoint=ep) == "https://example.com" + path

    def test_method_not_in_url(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep_get = _ep(method="GET", path="/v5/order/realtime")
        ep_post = _ep(method="POST", path="/v5/order/realtime")
        url_get = b.build(endpoint=ep_get)
        url_post = b.build(endpoint=ep_post)
        assert url_get == url_post

    def test_no_additional_slash(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(path="/v5/order/create")
        result = b.build(endpoint=ep)
        assert not result.startswith("https://example.com//")

    def test_no_slash_removed(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(path="/v5/position/list/")
        result = b.build(endpoint=ep)
        assert result.endswith("/")

    def test_base_url_not_modified(self):
        url = "https://example.com"
        b = BybitUrlBuilder(base_url=url)
        b.build(endpoint=_ep())
        assert b._base_url == url

    def test_endpoint_not_modified(self):
        b = _make_builder()
        ep = _ep(method="GET", path="/v5/order/realtime")
        b.build(endpoint=ep)
        assert ep.method == "GET"
        assert ep.path == "/v5/order/realtime"


# ── multiple calls ─────────────────────────────────────────────────────────

class TestMultipleCalls:
    def test_each_call_builds_correctly(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep1 = _ep(path="/v5/order/create")
        ep2 = _ep(path="/v5/order/cancel")
        assert b.build(endpoint=ep1) == "https://example.com/v5/order/create"
        assert b.build(endpoint=ep2) == "https://example.com/v5/order/cancel"

    def test_no_route_reuse(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep1 = _ep(path="/v5/order/create")
        ep2 = _ep(path="/v5/order/cancel")
        first = b.build(endpoint=ep1)
        second = b.build(endpoint=ep2)
        assert first != second

    def test_no_last_url_stored(self):
        b = _make_builder()
        b.build(endpoint=_ep())
        assert not hasattr(b, "last_url")

    def test_no_last_endpoint_stored(self):
        b = _make_builder()
        b.build(endpoint=_ep())
        assert not hasattr(b, "last_endpoint")

    def test_supports_different_endpoints_same_builder(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        paths = ["/v5/order/create", "/v5/order/cancel", "/v5/position/list"]
        results = [b.build(endpoint=_ep(path=p)) for p in paths]
        for i, path in enumerate(paths):
            assert results[i] == "https://example.com" + path


# ── no extra responsibilities ──────────────────────────────────────────────

class TestNoExtraResponsibilities:
    def test_no_sender_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "BybitPrivateRequestSender")

    def test_no_parser_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "BybitResponseParser")

    def test_no_transport_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_signer_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "MessageSigner")
        assert not hasattr(m, "HmacSha256Signer")

    def test_no_serializer_imported(self):
        import execution_gateway.bybit_url_builder as m
        assert not hasattr(m, "JsonSerializer")
        assert not hasattr(m, "StandardJsonSerializer")

    def test_no_hardcoded_bybit_url(self):
        import inspect
        import execution_gateway.bybit_url_builder as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src
        assert "api-demo" not in src

    def test_no_concrete_endpoints(self):
        import inspect
        import execution_gateway.bybit_url_builder as m
        src = inspect.getsource(m)
        assert "/v5/order" not in src
        assert "/v5/position" not in src

    def test_no_method_interpretation(self):
        b = BybitUrlBuilder(base_url="https://example.com")
        ep = _ep(method="GET", path="/v5/order/realtime")
        url = b.build(endpoint=ep)
        assert "GET" not in url
        assert "POST" not in url

    def test_no_http_execution(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        b = _make_builder()
        b.build(endpoint=_ep())
        assert called == []

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_endpoint import BybitEndpoint
        from execution_gateway.bybit_private_api import BybitPrivateApi
        assert GatewayConfig().environment == "demo"
        ep = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert ep.method == "GET"
