import socket
import urllib.error
import urllib.request

import pytest

import execution_gateway
from execution_gateway.urllib_get_http_transport import UrllibGetHttpTransport
from execution_gateway.http_get_transport import HttpGetTransport


class _FakeResponse:
    def __init__(self, body: bytes):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _install_fake_urlopen(monkeypatch, *, body=b'{"ok":true}', exc=None, capture=None):
    def fake(req, timeout=None):
        if capture is not None:
            capture.append(dict(
                method=req.get_method(), url=req.full_url,
                headers={k: v for k, v in req.header_items()},
                data=req.data, timeout=timeout,
            ))
        if exc is not None:
            raise exc
        return _FakeResponse(body)

    monkeypatch.setattr(urllib.request, "urlopen", fake)


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "UrllibGetHttpTransport")
        assert execution_gateway.UrllibGetHttpTransport is UrllibGetHttpTransport

    def test_in_all(self):
        assert "UrllibGetHttpTransport" in execution_gateway.__all__

    def test_satisfies_http_get_transport_protocol(self):
        assert isinstance(UrllibGetHttpTransport(), HttpGetTransport)


class TestValidation:
    def test_url_must_be_str(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="url must be str"):
            UrllibGetHttpTransport().get(url=1, headers={}, timeout_seconds=1)

    def test_url_must_not_be_empty(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(ValueError, match="url must not be empty"):
            UrllibGetHttpTransport().get(url="", headers={}, timeout_seconds=1)

    def test_headers_must_be_mapping(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="headers must be a Mapping"):
            UrllibGetHttpTransport().get(url="https://x", headers=[], timeout_seconds=1)

    def test_header_keys_must_be_str(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="header key must be str"):
            UrllibGetHttpTransport().get(url="https://x", headers={1: "a"}, timeout_seconds=1)

    def test_header_values_must_be_str(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="header value must be str"):
            UrllibGetHttpTransport().get(url="https://x", headers={"a": 1}, timeout_seconds=1)

    def test_timeout_must_be_numeric(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="timeout_seconds must be int or float"):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds="10")

    def test_timeout_rejects_bool(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(TypeError, match="timeout_seconds must be int or float"):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=True)

    def test_timeout_must_be_positive(self, monkeypatch):
        _install_fake_urlopen(monkeypatch)
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=0)


class TestBehavior:
    def test_returns_decoded_body(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b'{"hello":"world"}')
        result = UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)
        assert result == '{"hello":"world"}'

    def test_method_is_get(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(url="https://x/y", headers={}, timeout_seconds=1)
        assert calls[0]["method"] == "GET"

    def test_no_body_sent(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(url="https://x/y", headers={}, timeout_seconds=1)
        assert calls[0]["data"] is None

    def test_url_passed_through_exactly(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(
            url="https://api-demo.bybit.com/v5/position/list?category=linear",
            headers={}, timeout_seconds=1,
        )
        assert calls[0]["url"] == "https://api-demo.bybit.com/v5/position/list?category=linear"

    def test_headers_passed_through(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(
            url="https://x", headers={"X-Test": "abc"}, timeout_seconds=1,
        )
        assert calls[0]["headers"]["X-test"] == "abc"

    def test_timeout_passed_through(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=7.5)
        assert calls[0]["timeout"] == 7.5

    def test_socket_timeout_propagates(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, exc=socket.timeout("timed out"))
        with pytest.raises(socket.timeout):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)

    def test_http_error_propagates(self, monkeypatch):
        http_error = urllib.error.HTTPError("url", 403, "Forbidden", {}, None)
        _install_fake_urlopen(monkeypatch, exc=http_error)
        with pytest.raises(urllib.error.HTTPError):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)

    def test_invalid_utf8_propagates_raw(self, monkeypatch):
        _install_fake_urlopen(monkeypatch, body=b"\xff\xfe\x00")
        with pytest.raises(UnicodeDecodeError):
            UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)

    def test_exactly_one_call(self, monkeypatch):
        calls = []
        _install_fake_urlopen(monkeypatch, capture=calls)
        UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)
        assert len(calls) == 1


class TestResponseClose:
    """Deuda MENOR conocida desde el Hito 3.70 (cierre de Response sin test
    dedicado), cerrada en el Hito 3.72 al sumar un tercer consumidor
    periódico de este transporte compartido. Producción ya usa
    `with urllib.request.urlopen(...) as response:` correctamente -- este
    test convierte el mutante "eliminar el context manager" de superviviente
    a detectado, sin cambiar código de producción."""

    def test_response_used_as_context_manager(self, monkeypatch):
        entered = []
        exited = []

        class _TrackedResponse:
            def __init__(self, body: bytes):
                self._body = body

            def read(self):
                return self._body

            def __enter__(self):
                entered.append(1)
                return self

            def __exit__(self, *a):
                exited.append(1)
                return False

        def fake(req, timeout=None):
            return _TrackedResponse(b'{"ok":true}')

        monkeypatch.setattr(urllib.request, "urlopen", fake)
        UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)

        assert entered == [1]
        assert exited == [1]

    def test_response_exited_even_when_body_read_succeeds_before_return(self, monkeypatch):
        # El cierre debe ocurrir como parte del mismo `with`, no en un paso
        # posterior separable -- se verifica el orden: __exit__ ya ocurrió
        # para cuando `get()` retorna.
        exited = []

        class _TrackedResponse:
            def __init__(self, body: bytes):
                self._body = body

            def read(self):
                return self._body

            def __enter__(self):
                return self

            def __exit__(self, *a):
                exited.append(1)
                return False

        monkeypatch.setattr(urllib.request, "urlopen", lambda req, timeout=None: _TrackedResponse(b"{}"))
        UrllibGetHttpTransport().get(url="https://x", headers={}, timeout_seconds=1)
        assert exited == [1]
