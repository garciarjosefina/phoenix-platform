import os
import pytest
import execution_gateway
from execution_gateway.bybit_endpoint import BybitEndpoint


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_endpoint import BybitEndpoint as E
        assert E is BybitEndpoint

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitEndpoint")
        assert execution_gateway.BybitEndpoint is BybitEndpoint

    def test_in_all(self):
        assert "BybitEndpoint" in execution_gateway.__all__


# ── construcción válida ────────────────────────────────────────────────────

class TestValidConstruction:
    def test_method_get(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert e.method == "GET"

    def test_method_post(self):
        e = BybitEndpoint(method="POST", path="/v5/order/create")
        assert e.method == "POST"

    def test_path_simple(self):
        e = BybitEndpoint(method="GET", path="/v5/position/list")
        assert e.path == "/v5/position/list"

    def test_path_multiple_segments(self):
        e = BybitEndpoint(method="POST", path="/v5/order/cancel")
        assert e.path == "/v5/order/cancel"

    def test_path_with_query_string(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime?category=linear")
        assert e.path == "/v5/order/realtime?category=linear"

    def test_method_preserved_exactly(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert e.method == "GET"

    def test_path_preserved_exactly(self):
        path = "/v5/order/create"
        e = BybitEndpoint(method="POST", path=path)
        assert e.path is path


# ── validación de method ───────────────────────────────────────────────────

class TestMethodValidation:
    def test_rejects_non_str_method(self):
        with pytest.raises(TypeError):
            BybitEndpoint(method=123, path="/v5/order/create")

    def test_rejects_none_method(self):
        with pytest.raises(TypeError):
            BybitEndpoint(method=None, path="/v5/order/create")

    def test_rejects_empty_method(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="", path="/v5/order/create")

    def test_rejects_whitespace_method(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="   ", path="/v5/order/create")

    def test_rejects_lowercase_get(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="get", path="/v5/order/realtime")

    def test_rejects_lowercase_post(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="post", path="/v5/order/create")

    def test_rejects_get_with_spaces(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method=" GET ", path="/v5/order/realtime")

    def test_rejects_put(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="PUT", path="/v5/order/create")

    def test_rejects_patch(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="PATCH", path="/v5/order/create")

    def test_rejects_delete(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="DELETE", path="/v5/order/create")

    def test_rejects_head(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="HEAD", path="/v5/order/realtime")

    def test_rejects_unknown_method(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="OPTIONS", path="/v5/order/realtime")

    def test_no_normalization(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="get", path="/v5/order/realtime")

    def test_no_upper_conversion(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="post", path="/v5/order/create")


# ── validación de path ─────────────────────────────────────────────────────

class TestPathValidation:
    def test_rejects_non_str_path(self):
        with pytest.raises(TypeError):
            BybitEndpoint(method="GET", path=123)

    def test_rejects_none_path(self):
        with pytest.raises(TypeError):
            BybitEndpoint(method="GET", path=None)

    def test_rejects_empty_path(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="")

    def test_rejects_whitespace_path(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="   ")

    def test_rejects_path_without_leading_slash(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="v5/order/create")

    def test_rejects_path_double_leading_slash(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="//v5/order/create")

    def test_rejects_http_url(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="http://example.com/path")

    def test_rejects_https_url(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="https://api-demo.bybit.com/v5/order/create")

    def test_rejects_absolute_url_with_host(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="POST", path="https://example.com/v5/order/cancel")

    def test_accepts_query_string(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime?category=linear")
        assert e.path == "/v5/order/realtime?category=linear"

    def test_path_characters_preserved_exactly(self):
        path = "/v5/order/realtime?category=linear&symbol=BTCUSDT"
        e = BybitEndpoint(method="GET", path=path)
        assert e.path == path

    def test_no_strip_applied(self):
        with pytest.raises(ValueError):
            BybitEndpoint(method="GET", path="  /v5/order/realtime  ")

    def test_no_slash_added(self):
        path = "/v5/order/create"
        e = BybitEndpoint(method="POST", path=path)
        assert e.path == path

    def test_no_trailing_slash_removed(self):
        path = "/v5/position/list/"
        e = BybitEndpoint(method="GET", path=path)
        assert e.path == path

    def test_no_v5_prefix_required(self):
        e = BybitEndpoint(method="GET", path="/health")
        assert e.path == "/health"


# ── inmutabilidad ──────────────────────────────────────────────────────────

class TestImmutability:
    def test_is_frozen_dataclass(self):
        from dataclasses import fields, is_dataclass
        assert is_dataclass(BybitEndpoint)

    def test_equality_by_value(self):
        a = BybitEndpoint(method="GET", path="/v5/order/realtime")
        b = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert a == b

    def test_inequality_different_method(self):
        a = BybitEndpoint(method="GET", path="/v5/order/realtime")
        b = BybitEndpoint(method="POST", path="/v5/order/realtime")
        assert a != b

    def test_rejects_mutation_of_method(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        with pytest.raises(Exception):
            e.method = "POST"

    def test_rejects_mutation_of_path(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        with pytest.raises(Exception):
            e.path = "/v5/order/cancel"


# ── ausencia de comportamiento adicional ───────────────────────────────────

class TestNoBehavior:
    def test_no_url_attr(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert not hasattr(e, "url")

    def test_no_build_url(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert not hasattr(e, "build_url")

    def test_no_is_get(self):
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        assert not hasattr(e, "is_get")

    def test_no_is_post(self):
        e = BybitEndpoint(method="POST", path="/v5/order/create")
        assert not hasattr(e, "is_post")

    def test_no_extra_public_methods(self):
        import dataclasses
        e = BybitEndpoint(method="GET", path="/v5/order/realtime")
        field_names = {f.name for f in dataclasses.fields(e)}
        actual_public = {n for n in dir(e) if not n.startswith("_")}
        assert actual_public == field_names

    def test_no_http_transport_imported(self):
        import execution_gateway.bybit_endpoint as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_sender_imported(self):
        import execution_gateway.bybit_endpoint as m
        assert not hasattr(m, "BybitPrivateRequestSender")

    def test_no_parser_imported(self):
        import execution_gateway.bybit_endpoint as m
        assert not hasattr(m, "BybitResponseParser")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_endpoint as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_host_in_module(self):
        import inspect
        import execution_gateway.bybit_endpoint as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src

    def test_no_domain_in_module(self):
        import inspect
        import execution_gateway.bybit_endpoint as m
        src = inspect.getsource(m)
        assert "api-demo" not in src

    def test_no_base_url_in_module(self):
        import inspect
        import execution_gateway.bybit_endpoint as m
        src = inspect.getsource(m)
        assert "https://" not in src

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            e = BybitEndpoint(method="GET", path="/v5/order/realtime")
            assert e is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_response import BybitResponse
        from execution_gateway.bybit_private_api import BybitPrivateApi
        assert GatewayConfig().environment == "demo"
        r = BybitResponse(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1000)
        assert r.ret_code == 0
