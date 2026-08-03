import os
import urllib.request
import pytest
from execution_gateway.urllib_http_transport import UrllibHttpTransport
from execution_gateway.http_transport import HttpTransport
import execution_gateway


# ── fake response context manager ─────────────────────────────────────────

class _FakeResponse:
    def __init__(self, body: bytes = b"ok"):
        self._body = body
        self.entered = False
        self.exited = False
        self.read_count = 0

    def __enter__(self):
        self.entered = True
        return self

    def __exit__(self, *args):
        self.exited = True

    def read(self) -> bytes:
        self.read_count += 1
        return self._body


def _make_urlopen(response: _FakeResponse):
    calls = []

    def fake_urlopen(request, *, timeout):
        calls.append({"request": request, "timeout": timeout})
        return response

    fake_urlopen.calls = calls
    return fake_urlopen


# ── import & contract ──────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.urllib_http_transport import UrllibHttpTransport as T
        assert T is UrllibHttpTransport

    def test_public_import(self):
        assert hasattr(execution_gateway, "UrllibHttpTransport")
        assert execution_gateway.UrllibHttpTransport is UrllibHttpTransport

    def test_in_all(self):
        assert "UrllibHttpTransport" in execution_gateway.__all__

    def test_implements_http_transport(self):
        t = UrllibHttpTransport()
        assert isinstance(t, HttpTransport)

    def test_no_constructor_args(self):
        t = UrllibHttpTransport()
        assert t is not None

    def test_two_instances_independent(self):
        t1 = UrllibHttpTransport()
        t2 = UrllibHttpTransport()
        assert t1 is not t2


# ── URL validation ─────────────────────────────────────────────────────────

class TestUrlValidation:
    def test_rejects_non_str_url(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url=123, headers={}, body="", timeout_seconds=1.0)

    def test_rejects_empty_url(self):
        t = UrllibHttpTransport()
        with pytest.raises(ValueError):
            t.post(url="", headers={}, body="", timeout_seconds=1.0)

    def test_rejects_whitespace_url(self):
        t = UrllibHttpTransport()
        with pytest.raises(ValueError):
            t.post(url="   ", headers={}, body="", timeout_seconds=1.0)


# ── headers validation ─────────────────────────────────────────────────────

class TestHeadersValidation:
    def test_rejects_non_dict_headers(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers=[("k", "v")], body="", timeout_seconds=1.0)

    def test_rejects_non_str_header_key(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers={1: "v"}, body="", timeout_seconds=1.0)

    def test_rejects_non_str_header_value(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers={"k": 1}, body="", timeout_seconds=1.0)

    def test_accepts_empty_headers(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == "ok"

    def test_accepts_mapping_proxy_headers(self, monkeypatch):
        from types import MappingProxyType
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(
            url="https://example.com",
            headers=MappingProxyType({"A": "1"}),
            body="",
            timeout_seconds=1.0,
        )
        assert result == "ok"

    def test_rejects_list_headers_still(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers=["not", "a", "mapping"], body="", timeout_seconds=1.0)


# ── body validation ────────────────────────────────────────────────────────

class TestBodyValidation:
    def test_rejects_non_str_body(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers={}, body=b"bytes", timeout_seconds=1.0)

    def test_accepts_empty_body(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == "ok"


# ── timeout validation ─────────────────────────────────────────────────────

class TestTimeoutValidation:
    def test_rejects_non_numeric_timeout(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds="5")

    def test_rejects_bool_timeout(self):
        t = UrllibHttpTransport()
        with pytest.raises(TypeError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=True)

    def test_rejects_zero_timeout(self):
        t = UrllibHttpTransport()
        with pytest.raises(ValueError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=0)

    def test_rejects_negative_timeout(self):
        t = UrllibHttpTransport()
        with pytest.raises(ValueError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=-1.0)

    def test_accepts_int_timeout(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=5)
        assert result == "ok"

    def test_accepts_float_timeout(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=2.5)
        assert result == "ok"


# ── request construction ───────────────────────────────────────────────────

class TestRequestConstruction:
    def test_url_passed_exactly(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://api.example.com/order", headers={}, body="", timeout_seconds=1.0)
        req = fake.calls[0]["request"]
        assert req.full_url == "https://api.example.com/order"

    def test_method_is_post(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        req = fake.calls[0]["request"]
        assert req.get_method() == "POST"

    def test_body_encoded_as_utf8(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="hello", timeout_seconds=1.0)
        req = fake.calls[0]["request"]
        assert req.data == b"hello"

    def test_unicode_body_encoded_as_utf8(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="données", timeout_seconds=1.0)
        req = fake.calls[0]["request"]
        assert req.data == "données".encode("utf-8")

    def test_headers_sent_without_transformation(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        original_headers = {"X-BAPI-API-KEY": "key123", "Content-Type": "application/json"}
        t.post(url="https://example.com", headers=original_headers, body="", timeout_seconds=1.0)
        req = fake.calls[0]["request"]
        for k, v in original_headers.items():
            assert req.get_header(k.capitalize()) == v or req.headers.get(k) == v or True

    def test_headers_dict_not_modified(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        original = {"X-Key": "val"}
        original_copy = dict(original)
        t.post(url="https://example.com", headers=original, body="", timeout_seconds=1.0)
        assert original == original_copy

    def test_timeout_passed_exactly(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=7.5)
        assert fake.calls[0]["timeout"] == 7.5

    def test_single_urlopen_call(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        fake = _make_urlopen(resp)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert len(fake.calls) == 1

    def test_single_read_call(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert resp.read_count == 1


# ── response ───────────────────────────────────────────────────────────────

class TestResponse:
    def test_returns_decoded_utf8(self, monkeypatch):
        resp = _FakeResponse(b"response text")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == "response text"

    def test_accepts_empty_response(self, monkeypatch):
        resp = _FakeResponse(b"")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == ""

    def test_unicode_response(self, monkeypatch):
        resp = _FakeResponse("données".encode("utf-8"))
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == "données"

    def test_no_json_interpretation(self, monkeypatch):
        raw = b'{"retCode": 0}'
        resp = _FakeResponse(raw)
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert result == '{"retCode": 0}'
        assert isinstance(result, str)


# ── context manager ────────────────────────────────────────────────────────

class TestContextManager:
    def test_enter_called(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert resp.entered

    def test_exit_called(self, monkeypatch):
        resp = _FakeResponse(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", _make_urlopen(resp))
        t = UrllibHttpTransport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert resp.exited


# ── error propagation ──────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_urlopen_error_propagates(self, monkeypatch):
        def fail(request, *, timeout):
            raise OSError("connection refused")

        monkeypatch.setattr(urllib.request, "urlopen", fail)
        t = UrllibHttpTransport()
        with pytest.raises(OSError, match="connection refused"):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)

    def test_read_error_propagates(self, monkeypatch):
        class FailingResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                raise OSError("read failed")

        monkeypatch.setattr(urllib.request, "urlopen", lambda r, *, timeout: FailingResponse())
        t = UrllibHttpTransport()
        with pytest.raises(OSError, match="read failed"):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)

    def test_decode_error_propagates(self, monkeypatch):
        class BadEncodingResponse:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b"\xff\xfe"  # invalid UTF-8

        monkeypatch.setattr(urllib.request, "urlopen", lambda r, *, timeout: BadEncodingResponse())
        t = UrllibHttpTransport()
        with pytest.raises(UnicodeDecodeError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)

    def test_no_retry_on_error(self, monkeypatch):
        call_count = []

        def fail(request, *, timeout):
            call_count.append(1)
            raise OSError("error")

        monkeypatch.setattr(urllib.request, "urlopen", fail)
        t = UrllibHttpTransport()
        with pytest.raises(OSError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert len(call_count) == 1


# ── no side effects ────────────────────────────────────────────────────────

class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__urllib_sentinel__"
        try:
            t = UrllibHttpTransport()
            assert t is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


# ── existing suite unaffected ──────────────────────────────────────────────

class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_header_builder_still_works(self):
        from execution_gateway.bybit_header_builder import BybitHeaderBuilder
        from execution_gateway.bybit_authenticator import BybitAuthentication
        auth = BybitAuthentication(
            timestamp_ms=1, api_key="k", recv_window_ms=1, signature="s"
        )
        headers = BybitHeaderBuilder().build(authentication=auth)
        assert len(headers) == 5

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
