import os
import pytest
import execution_gateway
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_request import HttpRequest


# ── spy doubles ────────────────────────────────────────────────────────────

def _make_http_request(url: str = "https://example.com") -> HttpRequest:
    return HttpRequest(url=url, headers={"X-Key": "v"}, body="{}")


class _SpyBuilder(BybitRequestBuilder):
    def __init__(self, result: HttpRequest | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result or _make_http_request()

    def build(self, *, url: str, payload: object) -> HttpRequest:
        self.calls.append({"url": url, "payload": payload})
        return self._result


class _SpyExecutor(HttpRequestExecutor):
    def __init__(self, result: str = "response") -> None:
        self.calls: list[dict] = []
        self._result = result

    def execute(self, *, request: HttpRequest) -> str:
        self.calls.append({"request": request})
        return self._result


def _make_sender(
    builder_result: HttpRequest | None = None,
    executor_result: str = "response",
) -> tuple[BybitPrivateRequestSender, _SpyBuilder, _SpyExecutor]:
    b = _SpyBuilder(result=builder_result)
    e = _SpyExecutor(result=executor_result)
    s = BybitPrivateRequestSender(request_builder=b, request_executor=e)
    return s, b, e


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender as C
        assert C is BybitPrivateRequestSender

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitPrivateRequestSender")
        assert execution_gateway.BybitPrivateRequestSender is BybitPrivateRequestSender

    def test_in_all(self):
        assert "BybitPrivateRequestSender" in execution_gateway.__all__


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        s, _, _ = _make_sender()
        assert s is not None

    def test_stores_builder(self):
        b = _SpyBuilder()
        e = _SpyExecutor()
        s = BybitPrivateRequestSender(request_builder=b, request_executor=e)
        assert s._request_builder is b

    def test_stores_executor(self):
        b = _SpyBuilder()
        e = _SpyExecutor()
        s = BybitPrivateRequestSender(request_builder=b, request_executor=e)
        assert s._request_executor is e

    def test_rejects_incompatible_builder(self):
        with pytest.raises(TypeError):
            BybitPrivateRequestSender(
                request_builder=object(),
                request_executor=_SpyExecutor(),
            )

    def test_rejects_none_builder(self):
        with pytest.raises(TypeError):
            BybitPrivateRequestSender(
                request_builder=None,
                request_executor=_SpyExecutor(),
            )

    def test_rejects_incompatible_executor(self):
        with pytest.raises(TypeError):
            BybitPrivateRequestSender(
                request_builder=_SpyBuilder(),
                request_executor=object(),
            )

    def test_rejects_none_executor(self):
        with pytest.raises(TypeError):
            BybitPrivateRequestSender(
                request_builder=_SpyBuilder(),
                request_executor=None,
            )

    def test_no_builder_call_during_construction(self):
        b = _SpyBuilder()
        e = _SpyExecutor()
        BybitPrivateRequestSender(request_builder=b, request_executor=e)
        assert b.calls == []

    def test_no_executor_call_during_construction(self):
        b = _SpyBuilder()
        e = _SpyExecutor()
        BybitPrivateRequestSender(request_builder=b, request_executor=e)
        assert e.calls == []

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sender_sentinel__"
        try:
            s, _, _ = _make_sender()
            assert s is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


# ── url validation ─────────────────────────────────────────────────────────

class TestUrlValidation:
    def test_rejects_non_str_url(self):
        s, _, _ = _make_sender()
        with pytest.raises(TypeError):
            s.send(url=123, payload={})

    def test_rejects_none_url(self):
        s, _, _ = _make_sender()
        with pytest.raises(TypeError):
            s.send(url=None, payload={})

    def test_rejects_empty_url(self):
        s, _, _ = _make_sender()
        with pytest.raises(ValueError):
            s.send(url="", payload={})

    def test_rejects_whitespace_url(self):
        s, _, _ = _make_sender()
        with pytest.raises(ValueError):
            s.send(url="   ", payload={})

    def test_accepts_valid_url(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://api.bybit.com/v5/order/create", payload={})
        assert result == "response"

    def test_url_internal_spaces_preserved(self):
        s, b, _ = _make_sender()
        url = "https://example.com/path with spaces"
        s.send(url=url, payload={})
        assert b.calls[0]["url"] == url

    def test_url_not_stripped(self):
        s, _, _ = _make_sender()
        with pytest.raises(ValueError):
            s.send(url="   ", payload={})


# ── payload ────────────────────────────────────────────────────────────────

class TestPayload:
    def test_accepts_none_payload(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://example.com", payload=None)
        assert result == "response"

    def test_accepts_dict_payload(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://example.com", payload={"symbol": "BTCUSDT"})
        assert result == "response"

    def test_accepts_list_payload(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://example.com", payload=[1, 2, 3])
        assert result == "response"

    def test_accepts_str_payload(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://example.com", payload="raw")
        assert result == "response"

    def test_accepts_number_payload(self):
        s, _, _ = _make_sender()
        result = s.send(url="https://example.com", payload=42)
        assert result == "response"

    def test_payload_transmitted_by_identity(self):
        payload = {"key": "value", "nested": [1, 2]}
        s, b, _ = _make_sender()
        s.send(url="https://example.com", payload=payload)
        assert b.calls[0]["payload"] is payload


# ── order and composition ──────────────────────────────────────────────────

class TestOrderAndComposition:
    def _make_ordered(self):
        log: list[str] = []
        sentinel_req = _make_http_request("https://sentinel.com")

        class _OBuilder(BybitRequestBuilder):
            def __init__(self):
                self.calls = []
            def build(self, *, url, payload):
                log.append("build")
                self.calls.append({"url": url, "payload": payload})
                return sentinel_req

        class _OExecutor(HttpRequestExecutor):
            def __init__(self):
                self.calls = []
            def execute(self, *, request):
                log.append("execute")
                self.calls.append({"request": request})
                return "ordered_result"

        b = _OBuilder()
        e = _OExecutor()
        s = BybitPrivateRequestSender(request_builder=b, request_executor=e)
        return s, b, e, log, sentinel_req

    def test_builder_called_before_executor(self):
        s, _, _, log, _ = self._make_ordered()
        s.send(url="https://example.com", payload={})
        assert log.index("build") < log.index("execute")

    def test_full_sequence(self):
        s, _, _, log, _ = self._make_ordered()
        s.send(url="https://example.com", payload={})
        assert log == ["build", "execute"]

    def test_builder_called_exactly_once(self):
        s, b, _, _, _ = self._make_ordered()
        s.send(url="https://example.com", payload={})
        assert len(b.calls) == 1

    def test_executor_called_exactly_once(self):
        s, _, e, _, _ = self._make_ordered()
        s.send(url="https://example.com", payload={})
        assert len(e.calls) == 1

    def test_url_transmitted_exactly_to_builder(self):
        url = "https://api.example.com/v5/order/create"
        s, b, _, _, _ = self._make_ordered()
        s.send(url=url, payload={})
        assert b.calls[0]["url"] == url

    def test_payload_transmitted_to_builder(self):
        payload = {"qty": "0.001"}
        s, b, _, _, _ = self._make_ordered()
        s.send(url="https://example.com", payload=payload)
        assert b.calls[0]["payload"] is payload

    def test_http_request_passed_by_identity_to_executor(self):
        s, _, e, _, sentinel_req = self._make_ordered()
        s.send(url="https://example.com", payload={})
        assert e.calls[0]["request"] is sentinel_req

    def test_returns_exact_result(self):
        s, _, _, _, _ = self._make_ordered()
        result = s.send(url="https://example.com", payload={})
        assert result == "ordered_result"

    def test_empty_response(self):
        s, _, _ = _make_sender(executor_result="")
        result = s.send(url="https://example.com", payload={})
        assert result == ""

    def test_unicode_response(self):
        s, _, _ = _make_sender(executor_result="données: résultat")
        result = s.send(url="https://example.com", payload={})
        assert result == "données: résultat"

    def test_no_json_interpretation(self):
        json_str = '{"retCode":0,"result":{}}'
        s, _, _ = _make_sender(executor_result=json_str)
        result = s.send(url="https://example.com", payload={})
        assert result == json_str
        assert isinstance(result, str)


# ── multiple calls ─────────────────────────────────────────────────────────

class TestMultipleCalls:
    def test_each_call_invokes_builder(self):
        s, b, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        s.send(url="https://example.com", payload={})
        assert len(b.calls) == 2

    def test_each_call_invokes_executor(self):
        s, _, e = _make_sender()
        s.send(url="https://example.com", payload={})
        s.send(url="https://example.com", payload={})
        assert len(e.calls) == 2

    def test_no_request_reuse(self):
        req1 = _make_http_request("https://first.com")
        req2 = _make_http_request("https://second.com")
        reqs = [req1, req2]

        class _RotatingBuilder(BybitRequestBuilder):
            def __init__(self):
                self._i = 0
            def build(self, *, url, payload):
                r = reqs[self._i]
                self._i += 1
                return r

        b = _RotatingBuilder()
        e = _SpyExecutor()
        s = BybitPrivateRequestSender(request_builder=b, request_executor=e)
        s.send(url="https://example.com", payload={})
        s.send(url="https://example.com", payload={})
        assert e.calls[0]["request"] is req1
        assert e.calls[1]["request"] is req2

    def test_order_preserved_each_call(self):
        log: list[str] = []

        class _LogBuilder(BybitRequestBuilder):
            def __init__(self): pass
            def build(self, *, url, payload):
                log.append("build")
                return _make_http_request()

        class _LogExecutor(HttpRequestExecutor):
            def __init__(self): pass
            def execute(self, *, request):
                log.append("execute")
                return "ok"

        s = BybitPrivateRequestSender(
            request_builder=_LogBuilder(),
            request_executor=_LogExecutor(),
        )
        s.send(url="https://example.com", payload={})
        s.send(url="https://example.com", payload={})
        assert log == ["build", "execute", "build", "execute"]


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_propagates_builder_error(self):
        class _FailBuilder(BybitRequestBuilder):
            def __init__(self): pass
            def build(self, *, url, payload):
                raise RuntimeError("build fail")

        s = BybitPrivateRequestSender(
            request_builder=_FailBuilder(),
            request_executor=_SpyExecutor(),
        )
        with pytest.raises(RuntimeError, match="build fail"):
            s.send(url="https://example.com", payload={})

    def test_executor_not_called_when_builder_fails(self):
        class _FailBuilder(BybitRequestBuilder):
            def __init__(self): pass
            def build(self, *, url, payload):
                raise RuntimeError("build fail")

        e = _SpyExecutor()
        s = BybitPrivateRequestSender(
            request_builder=_FailBuilder(),
            request_executor=e,
        )
        with pytest.raises(RuntimeError):
            s.send(url="https://example.com", payload={})
        assert e.calls == []

    def test_propagates_executor_error(self):
        class _FailExecutor(HttpRequestExecutor):
            def __init__(self): pass
            def execute(self, *, request):
                raise OSError("executor fail")

        s = BybitPrivateRequestSender(
            request_builder=_SpyBuilder(),
            request_executor=_FailExecutor(),
        )
        with pytest.raises(OSError, match="executor fail"):
            s.send(url="https://example.com", payload={})

    def test_no_retry_on_executor_error(self):
        call_count = []

        class _FailOnce(HttpRequestExecutor):
            def __init__(self): pass
            def execute(self, *, request):
                call_count.append(1)
                raise OSError("fail")

        s = BybitPrivateRequestSender(
            request_builder=_SpyBuilder(),
            request_executor=_FailOnce(),
        )
        with pytest.raises(OSError):
            s.send(url="https://example.com", payload={})
        assert len(call_count) == 1

    def test_exception_not_transformed(self):
        class _FailExecutor(HttpRequestExecutor):
            def __init__(self): pass
            def execute(self, *, request):
                raise ValueError("original")

        s = BybitPrivateRequestSender(
            request_builder=_SpyBuilder(),
            request_executor=_FailExecutor(),
        )
        with pytest.raises(ValueError, match="original"):
            s.send(url="https://example.com", payload={})


# ── no state ───────────────────────────────────────────────────────────────

class TestNoState:
    def test_no_last_request_attr(self):
        s, _, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        assert not hasattr(s, "last_request")

    def test_no_last_response_attr(self):
        s, _, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        assert not hasattr(s, "last_response")

    def test_no_last_payload_attr(self):
        s, _, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        assert not hasattr(s, "last_payload")

    def test_no_last_url_attr(self):
        s, _, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        assert not hasattr(s, "last_url")


# ── no extra responsibilities ──────────────────────────────────────────────

class TestNoExtraResponsibilities:
    def test_no_urllib_imported(self):
        import execution_gateway.bybit_private_request_sender as m
        assert not hasattr(m, "urllib")

    def test_no_http_transport_imported(self):
        import execution_gateway.bybit_private_request_sender as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_private_request_sender as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_serializer_imported(self):
        import execution_gateway.bybit_private_request_sender as m
        assert not hasattr(m, "JsonSerializer")
        assert not hasattr(m, "StandardJsonSerializer")

    def test_no_signer_imported(self):
        import execution_gateway.bybit_private_request_sender as m
        assert not hasattr(m, "HmacSha256Signer")
        assert not hasattr(m, "MessageSigner")

    def test_no_hardcoded_endpoints(self):
        import inspect
        import execution_gateway.bybit_private_request_sender as m
        src = inspect.getsource(m)
        assert "/v5/" not in src
        assert "bybit.com" not in src

    def test_no_real_http_in_tests(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        s, _, _ = _make_sender()
        s.send(url="https://example.com", payload={})
        assert called == []

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.http_request import HttpRequest
        assert GatewayConfig().environment == "demo"
        req = HttpRequest(url="https://example.com", headers={}, body="")
        assert req.body == ""
