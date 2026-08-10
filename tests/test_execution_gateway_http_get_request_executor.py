import pytest

import execution_gateway
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor


class _SpyTransport:
    def __init__(self, *, result="body", exc=None):
        self.calls = []
        self._result = result
        self._exc = exc

    def get(self, *, url, headers, timeout_seconds):
        self.calls.append(dict(url=url, headers=headers, timeout_seconds=timeout_seconds))
        if self._exc is not None:
            raise self._exc
        return self._result


class _NotATransport:
    pass


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "HttpGetRequestExecutor")
        assert execution_gateway.HttpGetRequestExecutor is HttpGetRequestExecutor

    def test_in_all(self):
        assert "HttpGetRequestExecutor" in execution_gateway.__all__


class TestConstruction:
    def test_transport_must_satisfy_protocol(self):
        with pytest.raises(TypeError, match="HttpGetTransport"):
            HttpGetRequestExecutor(transport=_NotATransport(), timeout_seconds=10)

    def test_timeout_must_be_numeric(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float"):
            HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds="10")

    def test_timeout_rejects_bool(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float"):
            HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=True)

    def test_timeout_must_be_positive(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=0)

    def test_accepts_valid_construction(self):
        HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=10)


class TestExecute:
    def test_url_must_be_str(self):
        executor = HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=10)
        with pytest.raises(TypeError, match="url must be str"):
            executor.execute(url=1, headers={})

    def test_url_must_not_be_empty(self):
        executor = HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=10)
        with pytest.raises(ValueError, match="url must not be empty"):
            executor.execute(url="", headers={})

    def test_headers_must_be_mapping(self):
        executor = HttpGetRequestExecutor(transport=_SpyTransport(), timeout_seconds=10)
        with pytest.raises(TypeError, match="headers must be a Mapping"):
            executor.execute(url="https://x", headers=[])

    def test_delegates_to_transport_with_configured_timeout(self):
        transport = _SpyTransport()
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=12.5)
        executor.execute(url="https://x/y", headers={"a": "b"})
        assert transport.calls == [dict(url="https://x/y", headers={"a": "b"}, timeout_seconds=12.5)]

    def test_returns_transport_result(self):
        transport = _SpyTransport(result="raw-response")
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=10)
        assert executor.execute(url="https://x", headers={}) == "raw-response"

    def test_transport_error_propagates_unwrapped(self):
        transport = _SpyTransport(exc=OSError("boom"))
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=10)
        with pytest.raises(OSError, match="boom"):
            executor.execute(url="https://x", headers={})

    def test_exactly_one_transport_call(self):
        transport = _SpyTransport()
        executor = HttpGetRequestExecutor(transport=transport, timeout_seconds=10)
        executor.execute(url="https://x", headers={})
        assert len(transport.calls) == 1
