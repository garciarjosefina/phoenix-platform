import os
import pytest
import execution_gateway
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_response import BybitResponse


# ── helpers ────────────────────────────────────────────────────────────────

def _make_response(**kwargs) -> BybitResponse:
    defaults = dict(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1_000_000)
    return BybitResponse(**{**defaults, **kwargs})


_SENTINEL_URL = "https://example.com/v5/order/realtime"
_SENTINEL_RESPONSE = _make_response()


class _SpyBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyApi(BybitPrivateApi):
    def __init__(self, result: BybitResponse | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _SENTINEL_RESPONSE

    def request(self, *, url: str, payload: object) -> BybitResponse:
        self.calls.append({"url": url, "payload": payload})
        return self._result


def _make_executor(
    builder_result: str = _SENTINEL_URL,
    api_result: BybitResponse | None = None,
) -> tuple[BybitEndpointExecutor, _SpyBuilder, _SpyApi]:
    b = _SpyBuilder(result=builder_result)
    a = _SpyApi(result=api_result)
    ex = BybitEndpointExecutor(url_builder=b, private_api=a)
    return ex, b, a


def _ep(method: str = "GET", path: str = "/v5/order/realtime") -> BybitEndpoint:
    return BybitEndpoint(method=method, path=path)


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor as E
        assert E is BybitEndpointExecutor

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitEndpointExecutor")
        assert execution_gateway.BybitEndpointExecutor is BybitEndpointExecutor

    def test_in_all(self):
        assert "BybitEndpointExecutor" in execution_gateway.__all__

    def test_valid_construction(self):
        ex, _, _ = _make_executor()
        assert ex is not None


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_stores_url_builder(self):
        b = _SpyBuilder()
        a = _SpyApi()
        ex = BybitEndpointExecutor(url_builder=b, private_api=a)
        assert ex._url_builder is b

    def test_stores_private_api(self):
        b = _SpyBuilder()
        a = _SpyApi()
        ex = BybitEndpointExecutor(url_builder=b, private_api=a)
        assert ex._private_api is a

    def test_rejects_incompatible_builder(self):
        with pytest.raises(TypeError):
            BybitEndpointExecutor(url_builder=object(), private_api=_SpyApi())

    def test_rejects_none_builder(self):
        with pytest.raises(TypeError):
            BybitEndpointExecutor(url_builder=None, private_api=_SpyApi())

    def test_rejects_incompatible_api(self):
        with pytest.raises(TypeError):
            BybitEndpointExecutor(url_builder=_SpyBuilder(), private_api=object())

    def test_rejects_none_api(self):
        with pytest.raises(TypeError):
            BybitEndpointExecutor(url_builder=_SpyBuilder(), private_api=None)

    def test_no_builder_call_during_construction(self):
        b = _SpyBuilder()
        a = _SpyApi()
        BybitEndpointExecutor(url_builder=b, private_api=a)
        assert b.calls == []

    def test_no_api_call_during_construction(self):
        b = _SpyBuilder()
        a = _SpyApi()
        BybitEndpointExecutor(url_builder=b, private_api=a)
        assert a.calls == []

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            ex, _, _ = _make_executor()
            assert ex is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


# ── entrada ────────────────────────────────────────────────────────────────

class TestInput:
    def test_endpoint_must_be_keyword_only(self):
        ex, _, _ = _make_executor()
        ep = _ep()
        with pytest.raises(TypeError):
            ex.execute(ep, payload={})

    def test_payload_must_be_keyword_only(self):
        ex, _, _ = _make_executor()
        ep = _ep()
        with pytest.raises(TypeError):
            ex.execute(endpoint=ep)

    def test_rejects_incompatible_endpoint(self):
        ex, _, _ = _make_executor()
        with pytest.raises(TypeError):
            ex.execute(endpoint=object(), payload={})

    def test_accepts_get_endpoint(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(method="GET"), payload={})
        assert isinstance(result, BybitResponse)

    def test_accepts_post_endpoint(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(method="POST", path="/v5/order/create"), payload={})
        assert isinstance(result, BybitResponse)


# ── payload ────────────────────────────────────────────────────────────────

class TestPayload:
    def test_accepts_none_payload(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload=None)
        assert isinstance(result, BybitResponse)

    def test_accepts_dict_payload(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload={"symbol": "BTCUSDT"})
        assert isinstance(result, BybitResponse)

    def test_accepts_list_payload(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload=[1, 2, 3])
        assert isinstance(result, BybitResponse)

    def test_accepts_str_payload(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload="raw")
        assert isinstance(result, BybitResponse)

    def test_accepts_int_payload(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload=42)
        assert isinstance(result, BybitResponse)

    def test_payload_transmitted_by_identity(self):
        ex, _, a = _make_executor()
        payload = {"qty": "0.001"}
        ex.execute(endpoint=_ep(), payload=payload)
        assert a.calls[0]["payload"] is payload

    def test_none_payload_transmitted_as_none(self):
        ex, _, a = _make_executor()
        ex.execute(endpoint=_ep(), payload=None)
        assert a.calls[0]["payload"] is None

    def test_payload_not_copied(self):
        ex, _, a = _make_executor()
        payload = {"key": "value"}
        ex.execute(endpoint=_ep(), payload=payload)
        assert a.calls[0]["payload"] is payload

    def test_payload_not_transformed(self):
        ex, _, a = _make_executor()
        payload = [1, 2, 3]
        ex.execute(endpoint=_ep(), payload=payload)
        assert a.calls[0]["payload"] == [1, 2, 3]


# ── orden y composición ────────────────────────────────────────────────────

class TestOrderAndComposition:
    def _make_ordered(self, api_result: BybitResponse | None = None):
        log: list[str] = []
        sentinel_url = "https://example.com/v5/order/realtime"
        sentinel_response = api_result or _make_response()

        class _OrdBuilder(BybitUrlBuilder):
            def __init__(self):
                self.calls = []
            def build(self, *, endpoint):
                log.append("build")
                self.calls.append({"endpoint": endpoint})
                return sentinel_url

        class _OrdApi(BybitPrivateApi):
            def __init__(self):
                self.calls = []
            def request(self, *, url, payload):
                log.append("request")
                self.calls.append({"url": url, "payload": payload})
                return sentinel_response

        b = _OrdBuilder()
        a = _OrdApi()
        ex = BybitEndpointExecutor(url_builder=b, private_api=a)
        return ex, b, a, log, sentinel_url, sentinel_response

    def test_builder_called_before_api(self):
        ex, _, _, log, _, _ = self._make_ordered()
        ex.execute(endpoint=_ep(), payload={})
        assert log.index("build") < log.index("request")

    def test_full_sequence(self):
        ex, _, _, log, _, _ = self._make_ordered()
        ex.execute(endpoint=_ep(), payload={})
        assert log == ["build", "request"]

    def test_builder_called_exactly_once(self):
        ex, b, _, _, _, _ = self._make_ordered()
        ex.execute(endpoint=_ep(), payload={})
        assert len(b.calls) == 1

    def test_api_called_exactly_once(self):
        ex, _, a, _, _, _ = self._make_ordered()
        ex.execute(endpoint=_ep(), payload={})
        assert len(a.calls) == 1

    def test_endpoint_sent_by_identity_to_builder(self):
        ex, b, _, _, _, _ = self._make_ordered()
        ep = _ep()
        ex.execute(endpoint=ep, payload={})
        assert b.calls[0]["endpoint"] is ep

    def test_url_from_builder_sent_to_api(self):
        ex, _, a, _, sentinel_url, _ = self._make_ordered()
        ex.execute(endpoint=_ep(), payload={})
        assert a.calls[0]["url"] is sentinel_url

    def test_payload_sent_by_identity_to_api(self):
        ex, _, a, _, _, _ = self._make_ordered()
        payload = {"qty": "0.001"}
        ex.execute(endpoint=_ep(), payload=payload)
        assert a.calls[0]["payload"] is payload

    def test_response_returned_by_identity(self):
        sentinel = _make_response(ret_code=0)
        ex, _, _, _, _, sentinel_response = self._make_ordered(api_result=sentinel)
        result = ex.execute(endpoint=_ep(), payload={})
        assert result is sentinel_response

    def test_no_second_response_created(self):
        ex, _, _ = _make_executor()
        result = ex.execute(endpoint=_ep(), payload={})
        assert result is _SENTINEL_RESPONSE


# ── método HTTP ────────────────────────────────────────────────────────────

class TestHttpMethod:
    def test_does_not_inspect_method(self):
        ex, b, a = _make_executor()
        ep = _ep(method="GET", path="/v5/order/realtime")
        ex.execute(endpoint=ep, payload={})
        assert b.calls[0]["endpoint"] is ep

    def test_identical_behavior_get_and_post(self):
        log_get: list[str] = []
        log_post: list[str] = []

        class _LogBuilder(BybitUrlBuilder):
            def __init__(self, log):
                self._log = log
            def build(self, *, endpoint):
                self._log.append(endpoint.method)
                return "https://example.com/v5/order/realtime"

        class _LogApi(BybitPrivateApi):
            def __init__(self):
                pass
            def request(self, *, url, payload):
                return _SENTINEL_RESPONSE

        ex_get = BybitEndpointExecutor(
            url_builder=_LogBuilder(log_get), private_api=_LogApi()
        )
        ex_post = BybitEndpointExecutor(
            url_builder=_LogBuilder(log_post), private_api=_LogApi()
        )
        ep_get = _ep(method="GET")
        ep_post = _ep(method="POST", path="/v5/order/create")

        res_get = ex_get.execute(endpoint=ep_get, payload={})
        res_post = ex_post.execute(endpoint=ep_post, payload={})

        assert isinstance(res_get, BybitResponse)
        assert isinstance(res_post, BybitResponse)

    def test_method_not_passed_separately_to_api(self):
        ex, _, a = _make_executor()
        ex.execute(endpoint=_ep(method="GET"), payload={})
        api_call = a.calls[0]
        assert "method" not in api_call
        assert set(api_call.keys()) == {"url", "payload"}

    def test_no_branching_on_get(self):
        ex, b, _ = _make_executor()
        ep = _ep(method="GET")
        ex.execute(endpoint=ep, payload={})
        assert len(b.calls) == 1

    def test_no_branching_on_post(self):
        ex, b, _ = _make_executor()
        ep = _ep(method="POST", path="/v5/order/create")
        ex.execute(endpoint=ep, payload={})
        assert len(b.calls) == 1


# ── múltiples llamadas ─────────────────────────────────────────────────────

class TestMultipleCalls:
    def test_each_call_invokes_builder(self):
        ex, b, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        ex.execute(endpoint=_ep(), payload={})
        assert len(b.calls) == 2

    def test_each_call_invokes_api(self):
        ex, _, a = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        ex.execute(endpoint=_ep(), payload={})
        assert len(a.calls) == 2

    def test_no_url_reuse(self):
        urls = ["https://example.com/v5/order/create", "https://example.com/v5/order/cancel"]
        idx = [0]

        class _RotatingBuilder(BybitUrlBuilder):
            def __init__(self): pass
            def build(self, *, endpoint):
                url = urls[idx[0]]
                idx[0] += 1
                return url

        a = _SpyApi()
        ex = BybitEndpointExecutor(url_builder=_RotatingBuilder(), private_api=a)
        ex.execute(endpoint=_ep(), payload={})
        ex.execute(endpoint=_ep(), payload={})
        assert a.calls[0]["url"] == urls[0]
        assert a.calls[1]["url"] == urls[1]

    def test_order_preserved_each_call(self):
        log: list[str] = []

        class _LogBuilder(BybitUrlBuilder):
            def __init__(self): pass
            def build(self, *, endpoint):
                log.append("build")
                return "https://example.com/v5/order/realtime"

        class _LogApi(BybitPrivateApi):
            def __init__(self): pass
            def request(self, *, url, payload):
                log.append("request")
                return _SENTINEL_RESPONSE

        ex = BybitEndpointExecutor(url_builder=_LogBuilder(), private_api=_LogApi())
        ex.execute(endpoint=_ep(), payload={})
        ex.execute(endpoint=_ep(), payload={})
        assert log == ["build", "request", "build", "request"]

    def test_supports_different_endpoints(self):
        ex, b, _ = _make_executor()
        ep1 = _ep(path="/v5/order/create")
        ep2 = _ep(path="/v5/order/cancel")
        ex.execute(endpoint=ep1, payload={})
        ex.execute(endpoint=ep2, payload={})
        assert b.calls[0]["endpoint"] is ep1
        assert b.calls[1]["endpoint"] is ep2

    def test_supports_different_payloads(self):
        ex, _, a = _make_executor()
        p1 = {"qty": "0.001"}
        p2 = {"qty": "0.002"}
        ex.execute(endpoint=_ep(), payload=p1)
        ex.execute(endpoint=_ep(), payload=p2)
        assert a.calls[0]["payload"] is p1
        assert a.calls[1]["payload"] is p2


# ── errores ────────────────────────────────────────────────────────────────

class TestErrors:
    def test_propagates_builder_error(self):
        class _FailBuilder(BybitUrlBuilder):
            def __init__(self): pass
            def build(self, *, endpoint):
                raise RuntimeError("builder fail")

        ex = BybitEndpointExecutor(url_builder=_FailBuilder(), private_api=_SpyApi())
        with pytest.raises(RuntimeError, match="builder fail"):
            ex.execute(endpoint=_ep(), payload={})

    def test_api_not_called_when_builder_fails(self):
        class _FailBuilder(BybitUrlBuilder):
            def __init__(self): pass
            def build(self, *, endpoint):
                raise RuntimeError("builder fail")

        a = _SpyApi()
        ex = BybitEndpointExecutor(url_builder=_FailBuilder(), private_api=a)
        with pytest.raises(RuntimeError):
            ex.execute(endpoint=_ep(), payload={})
        assert a.calls == []

    def test_propagates_api_error(self):
        class _FailApi(BybitPrivateApi):
            def __init__(self): pass
            def request(self, *, url, payload):
                raise OSError("api fail")

        ex = BybitEndpointExecutor(url_builder=_SpyBuilder(), private_api=_FailApi())
        with pytest.raises(OSError, match="api fail"):
            ex.execute(endpoint=_ep(), payload={})

    def test_no_retry_on_api_error(self):
        call_count = []

        class _FailApi(BybitPrivateApi):
            def __init__(self): pass
            def request(self, *, url, payload):
                call_count.append(1)
                raise ValueError("fail")

        ex = BybitEndpointExecutor(url_builder=_SpyBuilder(), private_api=_FailApi())
        with pytest.raises(ValueError):
            ex.execute(endpoint=_ep(), payload={})
        assert len(call_count) == 1

    def test_no_exception_transformation_builder(self):
        class _FailBuilder(BybitUrlBuilder):
            def __init__(self): pass
            def build(self, *, endpoint):
                raise KeyError("original")

        ex = BybitEndpointExecutor(url_builder=_FailBuilder(), private_api=_SpyApi())
        with pytest.raises(KeyError, match="original"):
            ex.execute(endpoint=_ep(), payload={})

    def test_no_exception_transformation_api(self):
        class _FailApi(BybitPrivateApi):
            def __init__(self): pass
            def request(self, *, url, payload):
                raise TypeError("original")

        ex = BybitEndpointExecutor(url_builder=_SpyBuilder(), private_api=_FailApi())
        with pytest.raises(TypeError, match="original"):
            ex.execute(endpoint=_ep(), payload={})


# ── ausencia de estado y responsabilidades adicionales ─────────────────────

class TestNoState:
    def test_no_last_endpoint(self):
        ex, _, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        assert not hasattr(ex, "last_endpoint")

    def test_no_last_url(self):
        ex, _, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        assert not hasattr(ex, "last_url")

    def test_no_last_payload(self):
        ex, _, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        assert not hasattr(ex, "last_payload")

    def test_no_last_response(self):
        ex, _, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        assert not hasattr(ex, "last_response")


class TestNoExtraResponsibilities:
    def test_no_transport_imported(self):
        import execution_gateway.bybit_endpoint_executor as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_endpoint_executor as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_signer_imported(self):
        import execution_gateway.bybit_endpoint_executor as m
        assert not hasattr(m, "MessageSigner")
        assert not hasattr(m, "HmacSha256Signer")

    def test_no_serializer_imported(self):
        import execution_gateway.bybit_endpoint_executor as m
        assert not hasattr(m, "JsonSerializer")
        assert not hasattr(m, "StandardJsonSerializer")

    def test_no_clock_imported(self):
        import execution_gateway.bybit_endpoint_executor as m
        assert not hasattr(m, "MillisecondClock")
        assert not hasattr(m, "SystemMillisecondClock")

    def test_no_base_url_in_module(self):
        import inspect
        import execution_gateway.bybit_endpoint_executor as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src
        assert "https://" not in src

    def test_no_concrete_endpoints_in_module(self):
        import inspect
        import execution_gateway.bybit_endpoint_executor as m
        src = inspect.getsource(m)
        assert "/v5/order" not in src
        assert "/v5/position" not in src

    def test_no_ret_code_interpretation(self):
        ex, _, _ = _make_executor(api_result=_make_response(ret_code=10001))
        result = ex.execute(endpoint=_ep(), payload={})
        assert result.ret_code == 10001

    def test_no_real_http(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        ex, _, _ = _make_executor()
        ex.execute(endpoint=_ep(), payload={})
        assert called == []

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_endpoint import BybitEndpoint
        from execution_gateway.bybit_url_builder import BybitUrlBuilder
        assert GatewayConfig().environment == "demo"
        ep = BybitEndpoint(method="GET", path="/v5/order/realtime")
        b = BybitUrlBuilder(base_url="https://example.com")
        assert b.build(endpoint=ep) == "https://example.com/v5/order/realtime"
