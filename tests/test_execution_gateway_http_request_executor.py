import os
import pytest
import execution_gateway
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_request import HttpRequest
from execution_gateway.http_transport import HttpTransport


# ── helpers ────────────────────────────────────────────────────────────────

def _make_request(
    url: str = "https://example.com/order",
    headers: dict | None = None,
    body: str = '{"qty":"1"}',
) -> HttpRequest:
    return HttpRequest(
        url=url,
        headers=headers if headers is not None else {"X-Key": "val"},
        body=body,
    )


class _FakeTransport:
    def __init__(self, result: str = "ok") -> None:
        self._result = result
        self.calls: list[dict] = []

    def post(self, *, url: str, headers, body: str, timeout_seconds: float) -> str:
        self.calls.append(
            {"url": url, "headers": headers, "body": body, "timeout_seconds": timeout_seconds}
        )
        return self._result


def _make_executor(
    result: str = "ok",
    timeout: float = 5.0,
) -> tuple[HttpRequestExecutor, _FakeTransport]:
    t = _FakeTransport(result=result)
    e = HttpRequestExecutor(transport=t, timeout_seconds=timeout)
    return e, t


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.http_request_executor import HttpRequestExecutor as E
        assert E is HttpRequestExecutor

    def test_public_import(self):
        assert hasattr(execution_gateway, "HttpRequestExecutor")
        assert execution_gateway.HttpRequestExecutor is HttpRequestExecutor

    def test_in_all(self):
        assert "HttpRequestExecutor" in execution_gateway.__all__


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        e, _ = _make_executor()
        assert e is not None

    def test_accepts_structural_transport(self):
        class _DuckTransport:
            def post(self, *, url, headers, body, timeout_seconds):
                return ""

        assert isinstance(_DuckTransport(), HttpTransport)
        e = HttpRequestExecutor(transport=_DuckTransport(), timeout_seconds=1.0)
        assert e is not None

    def test_stores_transport(self):
        t = _FakeTransport()
        e = HttpRequestExecutor(transport=t, timeout_seconds=1.0)
        assert e._transport is t

    def test_stores_timeout(self):
        e = HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=7.5)
        assert e._timeout_seconds == 7.5

    def test_rejects_incompatible_transport(self):
        with pytest.raises(TypeError):
            HttpRequestExecutor(transport=object(), timeout_seconds=1.0)

    def test_rejects_none_transport(self):
        with pytest.raises(TypeError):
            HttpRequestExecutor(transport=None, timeout_seconds=1.0)

    def test_rejects_non_numeric_timeout(self):
        with pytest.raises(TypeError):
            HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds="5")

    def test_rejects_bool_timeout(self):
        with pytest.raises(TypeError):
            HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=True)

    def test_rejects_zero_timeout(self):
        with pytest.raises(ValueError):
            HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=0)

    def test_rejects_negative_timeout(self):
        with pytest.raises(ValueError):
            HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=-1.0)

    def test_accepts_int_timeout(self):
        e = HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=10)
        assert e._timeout_seconds == 10

    def test_accepts_float_timeout(self):
        e = HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=2.5)
        assert e._timeout_seconds == 2.5

    def test_no_transport_call_during_construction(self):
        t = _FakeTransport()
        HttpRequestExecutor(transport=t, timeout_seconds=1.0)
        assert t.calls == []

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__executor_sentinel__"
        try:
            e = HttpRequestExecutor(transport=_FakeTransport(), timeout_seconds=1.0)
            assert e is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


# ── execute ────────────────────────────────────────────────────────────────

class TestExecute:
    def test_request_is_keyword_only(self):
        e, _ = _make_executor()
        req = _make_request()
        with pytest.raises(TypeError):
            e.execute(req)

    def test_rejects_incompatible_request(self):
        e, _ = _make_executor()
        with pytest.raises(TypeError):
            e.execute(request=object())

    def test_rejects_none_request(self):
        e, _ = _make_executor()
        with pytest.raises(TypeError):
            e.execute(request=None)

    def test_calls_transport_post(self):
        e, t = _make_executor()
        e.execute(request=_make_request())
        assert len(t.calls) == 1

    def test_url_transmitted_exactly(self):
        url = "https://api.bybit.com/v5/order/create"
        e, t = _make_executor()
        e.execute(request=_make_request(url=url))
        assert t.calls[0]["url"] == url

    def test_headers_transmitted_exactly(self):
        headers = {"X-BAPI-API-KEY": "key123", "Content-Type": "application/json"}
        e, t = _make_executor()
        e.execute(request=_make_request(headers=headers))
        assert t.calls[0]["headers"] == headers

    def test_body_transmitted_exactly(self):
        body = '{"symbol":"BTCUSDT","qty":"0.001"}'
        e, t = _make_executor()
        e.execute(request=_make_request(body=body))
        assert t.calls[0]["body"] == body

    def test_timeout_transmitted_exactly(self):
        e, t = _make_executor(timeout=12.3)
        e.execute(request=_make_request())
        assert t.calls[0]["timeout_seconds"] == 12.3

    def test_single_transport_call(self):
        e, t = _make_executor()
        e.execute(request=_make_request())
        assert len(t.calls) == 1

    def test_returns_exact_result(self):
        sentinel = "response_body_xyz_42"
        e, _ = _make_executor(result=sentinel)
        result = e.execute(request=_make_request())
        assert result == sentinel

    def test_result_is_string(self):
        e, _ = _make_executor(result="any result")
        result = e.execute(request=_make_request())
        assert isinstance(result, str)

    def test_empty_response(self):
        e, _ = _make_executor(result="")
        result = e.execute(request=_make_request())
        assert result == ""

    def test_unicode_response(self):
        e, _ = _make_executor(result="données: résultat")
        result = e.execute(request=_make_request())
        assert result == "données: résultat"

    def test_no_json_interpretation(self):
        json_str = '{"retCode":0,"result":{}}'
        e, _ = _make_executor(result=json_str)
        result = e.execute(request=_make_request())
        assert result == json_str
        assert isinstance(result, str)

    def test_does_not_modify_http_request(self):
        req = _make_request(url="https://example.com", headers={"K": "V"}, body="b")
        e, _ = _make_executor()
        e.execute(request=req)
        assert req.url == "https://example.com"
        assert req.body == "b"

    def test_does_not_modify_headers(self):
        headers = {"X-Key": "original"}
        req = _make_request(headers=headers)
        headers_before = dict(req.headers)
        e, _ = _make_executor()
        e.execute(request=req)
        assert req.headers == headers_before

    def test_new_transport_call_each_execution(self):
        e, t = _make_executor()
        req = _make_request()
        e.execute(request=req)
        e.execute(request=req)
        assert len(t.calls) == 2


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_propagates_transport_exception(self):
        class _FailTransport:
            def post(self, *, url, headers, body, timeout_seconds):
                raise OSError("connection refused")

        e = HttpRequestExecutor(transport=_FailTransport(), timeout_seconds=1.0)
        with pytest.raises(OSError, match="connection refused"):
            e.execute(request=_make_request())

    def test_no_retry_on_error(self):
        call_count = []

        class _FailOnce:
            def post(self, *, url, headers, body, timeout_seconds):
                call_count.append(1)
                raise OSError("fail")

        e = HttpRequestExecutor(transport=_FailOnce(), timeout_seconds=1.0)
        with pytest.raises(OSError):
            e.execute(request=_make_request())
        assert len(call_count) == 1

    def test_exception_not_transformed(self):
        class _FailTransport:
            def post(self, *, url, headers, body, timeout_seconds):
                raise ValueError("original error")

        e = HttpRequestExecutor(transport=_FailTransport(), timeout_seconds=1.0)
        with pytest.raises(ValueError, match="original error"):
            e.execute(request=_make_request())


# ── no state ───────────────────────────────────────────────────────────────

class TestNoState:
    def test_no_last_request_attr(self):
        e, _ = _make_executor()
        e.execute(request=_make_request())
        assert not hasattr(e, "last_request")

    def test_no_last_response_attr(self):
        e, _ = _make_executor()
        e.execute(request=_make_request())
        assert not hasattr(e, "last_response")

    def test_no_last_error_attr(self):
        e, _ = _make_executor()
        assert not hasattr(e, "last_error")


# ── no business knowledge ──────────────────────────────────────────────────

class TestNoBusinessKnowledge:
    def test_no_bybit_request_builder_imported(self):
        import execution_gateway.http_request_executor as m
        assert not hasattr(m, "BybitRequestBuilder")

    def test_no_authenticator_imported(self):
        import execution_gateway.http_request_executor as m
        assert not hasattr(m, "BybitAuthenticator")
        assert not hasattr(m, "StandardBybitAuthenticator")

    def test_no_signer_imported(self):
        import execution_gateway.http_request_executor as m
        assert not hasattr(m, "HmacSha256Signer")
        assert not hasattr(m, "MessageSigner")

    def test_no_serializer_imported(self):
        import execution_gateway.http_request_executor as m
        assert not hasattr(m, "JsonSerializer")
        assert not hasattr(m, "StandardJsonSerializer")

    def test_no_urllib_imported(self):
        import execution_gateway.http_request_executor as m
        assert not hasattr(m, "urllib")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_real_http_in_tests(self, monkeypatch):
        import urllib.request
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(1))
        e, _ = _make_executor()
        e.execute(request=_make_request())
        assert called == []

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.http_request import HttpRequest
        assert GatewayConfig().environment == "demo"
        req = HttpRequest(url="https://example.com", headers={}, body="")
        assert req.body == ""
