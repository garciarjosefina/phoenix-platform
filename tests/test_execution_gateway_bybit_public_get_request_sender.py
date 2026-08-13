import pytest

import execution_gateway
from execution_gateway.bybit_public_get_request_sender import BybitPublicGetRequestSender
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor


class _SpyTransport:
    """Test double for HttpGetTransport -- satisfies the Protocol structurally."""

    def __init__(self, *, result="body"):
        self.calls = []
        self._result = result

    def get(self, *, url, headers, timeout_seconds):
        self.calls.append(dict(url=url, headers=headers, timeout_seconds=timeout_seconds))
        return self._result


def _executor(*, result="body"):
    transport = _SpyTransport(result=result)
    return HttpGetRequestExecutor(transport=transport, timeout_seconds=10), transport


def _sender(*, request_executor=None):
    executor, transport = (request_executor, None) if request_executor is not None else _executor()
    return BybitPublicGetRequestSender(request_executor=executor), transport


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPublicGetRequestSender")
        assert execution_gateway.BybitPublicGetRequestSender is BybitPublicGetRequestSender

    def test_in_all(self):
        assert "BybitPublicGetRequestSender" in execution_gateway.__all__


class TestConstruction:
    def test_request_executor_must_be_correct_type(self):
        with pytest.raises(TypeError, match="HttpGetRequestExecutor"):
            BybitPublicGetRequestSender(request_executor=object())

    def test_does_not_require_authenticator(self):
        # A diferencia de BybitPrivateGetRequestSender, no toma ni
        # authenticator ni header_builder -- verificado por firma.
        import inspect
        params = inspect.signature(BybitPublicGetRequestSender.__init__).parameters
        assert "authenticator" not in params
        assert "header_builder" not in params


class TestSend:
    def test_url_must_be_str(self):
        sender, _ = _sender()
        with pytest.raises(TypeError, match="url must be str"):
            sender.send(url=1, query_string="")

    def test_url_must_not_be_empty(self):
        sender, _ = _sender()
        with pytest.raises(ValueError, match="url must not be empty"):
            sender.send(url="", query_string="")

    def test_query_string_must_be_str(self):
        sender, _ = _sender()
        with pytest.raises(TypeError, match="query_string must be str"):
            sender.send(url="https://x", query_string=None)

    def test_query_string_appended_to_url(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x/y", query_string="category=linear&symbol=BTCUSDT")
        assert transport.calls[0]["url"] == "https://x/y?category=linear&symbol=BTCUSDT"

    def test_empty_query_string_does_not_append_question_mark(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x/y", query_string="")
        assert transport.calls[0]["url"] == "https://x/y"

    def test_no_authentication_headers_sent(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x", query_string="")
        headers = transport.calls[0]["headers"]
        assert headers == {}

    def test_no_x_bapi_headers_present(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x", query_string="")
        headers = transport.calls[0]["headers"]
        assert not any(k.upper().startswith("X-BAPI") for k in headers)

    def test_returns_executor_result(self):
        executor, _ = _executor(result="raw-json")
        sender, _ = _sender(request_executor=executor)
        assert sender.send(url="https://x", query_string="") == "raw-json"

    def test_exactly_one_transport_call(self):
        executor, transport = _executor()
        sender, _ = _sender(request_executor=executor)
        sender.send(url="https://x", query_string="a=b")
        assert len(transport.calls) == 1

    def test_no_credentials_referenced_in_source(self):
        # Sólo código real (sin comentarios) -- el módulo documenta en
        # prosa por qué NO usa HMAC, lo cual mencionaría la palabra.
        import inspect
        import execution_gateway.bybit_public_get_request_sender as module
        code_lines = [
            line for line in inspect.getsource(module).splitlines()
            if not line.strip().startswith("#")
        ]
        code = "\n".join(code_lines).lower()
        assert "api_key" not in code
        assert "api_secret" not in code
        assert "credentials" not in code
        assert "signer" not in code
        assert "hmac" not in code
        assert "authenticat" not in code
        assert "header_builder" not in code
