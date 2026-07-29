import inspect
import urllib.request

import pytest

import execution_gateway
import execution_gateway.http_transport_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport import HttpTransport
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.urllib_http_transport import UrllibHttpTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, body: bytes = b'{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'):
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self) -> bytes:
        return self._body


def _make_urlopen(result: bytes = b'{"retCode":0}'):
    calls: list[dict] = []

    def fake_urlopen(request, *, timeout):
        calls.append({"request": request, "timeout": timeout})
        return _FakeResponse(result)

    fake_urlopen.calls = calls
    return fake_urlopen


class SpyAuthenticator:
    def __init__(self) -> None:
        self.calls: list = []

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.calls.append({"body": body})
        return BybitAuthentication(
            timestamp_ms=1_700_000_000_000,
            api_key="test_key",
            recv_window_ms=5_000,
            signature="abcdef0123456789" * 4,
        )


class SpyHeaderBuilder(BybitHeaderBuilder):
    def __init__(self) -> None:
        self.calls: list = []

    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        self.calls.append({"authentication": authentication})
        return super().build(authentication=authentication)


class SpySerializer:
    def __init__(self) -> None:
        self.dumps_calls: list = []

    def dumps(self, v: object) -> str:
        self.dumps_calls.append(v)
        return "{}"

    def loads(self, v: str) -> object:
        return {}


class SpyParserSerializer:
    def dumps(self, v: object) -> str:
        return "{}"

    def loads(self, v: str) -> object:
        return {"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": 1000}


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.http_transport_factory import create_http_transport as f
        assert f is create_http_transport

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_http_transport")
        assert execution_gateway.create_http_transport is create_http_transport

    def test_included_in_all(self):
        assert "create_http_transport" in execution_gateway.__all__

    def test_single_factory_for_http_transport(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "transport" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_http_transport"

    def test_callable(self):
        assert callable(create_http_transport)

    def test_no_extra_args_accepted(self):
        with pytest.raises(TypeError):
            create_http_transport(object())

    def test_return_annotation_is_urllib_http_transport(self):
        hints = inspect.get_annotations(create_http_transport, eval_str=True)
        assert hints.get("return") is UrllibHttpTransport


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_zero_parameters(self):
        sig = inspect.signature(create_http_transport)
        assert len(sig.parameters) == 0

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_http_transport)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_http_transport)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_client(self):
        sig = inspect.signature(create_http_transport)
        assert "client" not in sig.parameters

    def test_does_not_receive_session(self):
        sig = inspect.signature(create_http_transport)
        assert "session" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_http_transport)
        assert "base_url" not in sig.parameters

    def test_does_not_receive_timeout(self):
        sig = inspect.signature(create_http_transport)
        assert "timeout_seconds" not in sig.parameters
        assert "timeout" not in sig.parameters

    def test_does_not_receive_retry_policy(self):
        sig = inspect.signature(create_http_transport)
        assert "retry" not in sig.parameters
        assert "max_retries" not in sig.parameters


# ---------------------------------------------------------------------------
# 3. Implementación concreta
# ---------------------------------------------------------------------------

class TestConcreteImplementation:
    def test_returns_urllib_http_transport(self):
        t = create_http_transport()
        assert isinstance(t, UrllibHttpTransport)

    def test_returns_exact_type(self):
        t = create_http_transport()
        assert type(t) is UrllibHttpTransport

    def test_satisfies_http_transport_protocol(self):
        t = create_http_transport()
        assert isinstance(t, HttpTransport)

    def test_not_a_fake(self):
        t = create_http_transport()
        assert type(t).__name__ == "UrllibHttpTransport"

    def test_not_the_protocol(self):
        t = create_http_transport()
        assert type(t) is not HttpTransport

    def test_has_post_method(self):
        t = create_http_transport()
        assert callable(getattr(t, "post", None))


# ---------------------------------------------------------------------------
# 4. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_new_instance_each_call(self):
        t1 = create_http_transport()
        t2 = create_http_transport()
        assert t1 is not t2

    def test_two_instances_are_independent(self):
        t1 = create_http_transport()
        t2 = create_http_transport()
        assert t1 is not t2
        assert isinstance(t1, UrllibHttpTransport)
        assert isinstance(t2, UrllibHttpTransport)

    def test_does_not_return_tuple(self):
        t = create_http_transport()
        assert not isinstance(t, tuple)

    def test_does_not_return_dict(self):
        t = create_http_transport()
        assert not isinstance(t, dict)

    def test_does_not_return_none(self):
        t = create_http_transport()
        assert t is not None

    def test_does_not_return_class(self):
        t = create_http_transport()
        assert not inspect.isclass(t)


# ---------------------------------------------------------------------------
# 5. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_three_calls_produce_distinct_transports(self):
        t1 = create_http_transport()
        t2 = create_http_transport()
        t3 = create_http_transport()
        assert t1 is not t2
        assert t2 is not t3
        assert t1 is not t3

    def test_each_instance_is_urllib_http_transport(self):
        for _ in range(3):
            t = create_http_transport()
            assert type(t) is UrllibHttpTransport

    def test_no_singleton_behavior(self):
        instances = [create_http_transport() for _ in range(5)]
        ids = [id(t) for t in instances]
        assert len(set(ids)) == 5

    def test_no_shared_state_between_calls(self):
        t1 = create_http_transport()
        t2 = create_http_transport()
        assert t1 is not t2


# ---------------------------------------------------------------------------
# 6. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_urlopen_not_called_during_construction(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(True))
        create_http_transport()
        assert called == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_http_transport()
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        t = create_http_transport()
        assert isinstance(t, UrllibHttpTransport)

    def test_no_dns_during_construction(self, monkeypatch):
        import socket
        dns_calls = []
        original = socket.getaddrinfo

        def patched(*args, **kwargs):
            dns_calls.append(args)
            return original(*args, **kwargs)

        socket.getaddrinfo = patched
        try:
            create_http_transport()
        finally:
            socket.getaddrinfo = original
        assert dns_calls == []


# ---------------------------------------------------------------------------
# 7. Comportamiento integrado mínimo del transporte
# ---------------------------------------------------------------------------

class TestIntegratedTransportBehavior:
    def test_post_returns_decoded_response(self, monkeypatch):
        fake = _make_urlopen(b'{"retCode":0}')
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        result = t.post(url="https://api-demo.bybit.com/v5/order/create", headers={}, body="{}", timeout_seconds=5.0)
        assert result == '{"retCode":0}'

    def test_post_returns_string(self, monkeypatch):
        fake = _make_urlopen(b"ok")
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        result = t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert isinstance(result, str)

    def test_post_calls_urlopen_exactly_once(self, monkeypatch):
        fake = _make_urlopen()
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        t.post(url="https://example.com", headers={}, body="{}", timeout_seconds=5.0)
        assert len(fake.calls) == 1

    def test_post_passes_url_to_urlopen(self, monkeypatch):
        fake = _make_urlopen()
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        t.post(url="https://api-demo.bybit.com/v5/order/create", headers={}, body="{}", timeout_seconds=5.0)
        assert fake.calls[0]["request"].full_url == "https://api-demo.bybit.com/v5/order/create"

    def test_post_passes_timeout_to_urlopen(self, monkeypatch):
        fake = _make_urlopen()
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=12.3)
        assert fake.calls[0]["timeout"] == 12.3

    def test_post_uses_http_post_method(self, monkeypatch):
        fake = _make_urlopen()
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert fake.calls[0]["request"].get_method() == "POST"

    def test_urlopen_error_propagates(self, monkeypatch):
        err = OSError("connection refused")

        def fail(request, *, timeout):
            raise err

        monkeypatch.setattr(urllib.request, "urlopen", fail)
        t = create_http_transport()
        with pytest.raises(OSError) as exc_info:
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert exc_info.value is err

    def test_no_retry_after_error(self, monkeypatch):
        call_count = []

        def fail(request, *, timeout):
            call_count.append(1)
            raise OSError("error")

        monkeypatch.setattr(urllib.request, "urlopen", fail)
        t = create_http_transport()
        with pytest.raises(OSError):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)
        assert len(call_count) == 1

    def test_error_not_wrapped(self, monkeypatch):
        monkeypatch.setattr(urllib.request, "urlopen", lambda r, *, timeout: (_ for _ in ()).throw(ValueError("raw error")))
        t = create_http_transport()
        with pytest.raises(ValueError, match="raw error"):
            t.post(url="https://example.com", headers={}, body="", timeout_seconds=1.0)

    def test_response_not_modified(self, monkeypatch):
        raw = b'{"retCode":0,"retMsg":"OK","result":{"orderId":"abc123"}}'
        fake = _make_urlopen(raw)
        monkeypatch.setattr(urllib.request, "urlopen", fake)
        t = create_http_transport()
        result = t.post(url="https://example.com", headers={}, body="{}", timeout_seconds=5.0)
        assert result == raw.decode("utf-8")


# ---------------------------------------------------------------------------
# 8. Integración compositiva completa
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def _build_full_stack(self):
        spy_authenticator = SpyAuthenticator()
        spy_header_builder = SpyHeaderBuilder()
        spy_serializer = SpySerializer()
        spy_parser_serializer = SpyParserSerializer()

        transport = create_http_transport()
        executor = create_http_request_executor(transport=transport, timeout_seconds=5.0)
        request_builder = create_bybit_request_builder(
            serializer=spy_serializer,
            authenticator=spy_authenticator,
            header_builder=spy_header_builder,
        )
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=executor,
        )
        parser = create_bybit_response_parser(serializer=spy_parser_serializer)
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)
        gateway = create_bybit_demo_execution_gateway(private_api=private_api)

        return (
            gateway,
            transport,
            executor,
            sender,
            parser,
            private_api,
            request_builder,
            spy_authenticator,
            spy_header_builder,
            spy_serializer,
        )

    def test_full_stack_builds_correctly(self):
        gateway, *_ = self._build_full_stack()
        assert isinstance(gateway, BybitExecutionGateway)

    def test_transport_identity_in_executor(self):
        _, transport, executor, *_ = self._build_full_stack()
        assert executor._transport is transport

    def test_executor_identity_in_sender(self):
        _, _, executor, sender, *_ = self._build_full_stack()
        assert sender._request_executor is executor

    def test_builder_identity_in_sender(self):
        _, _, _, sender, _, _, request_builder, *_ = self._build_full_stack()
        assert sender._request_builder is request_builder

    def test_sender_identity_in_private_api(self):
        _, _, _, sender, _, private_api, *_ = self._build_full_stack()
        assert private_api._sender is sender

    def test_parser_identity_in_private_api(self):
        _, _, _, _, parser, private_api, *_ = self._build_full_stack()
        assert private_api._response_parser is parser

    def test_no_urlopen_during_composition(self, monkeypatch):
        called = []
        monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **kw: called.append(True))
        gateway, *_ = self._build_full_stack()
        assert called == []

    def test_no_auth_during_composition(self):
        _, _, _, _, _, _, _, spy_authenticator, spy_header_builder, spy_serializer = self._build_full_stack()
        assert spy_authenticator.calls == []
        assert spy_header_builder.calls == []
        assert spy_serializer.dumps_calls == []


# ---------------------------------------------------------------------------
# 9. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_requests(self):
        assert "requests" not in vars(_module)

    def test_does_not_import_httpx(self):
        assert "httpx" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_serializer(self):
        assert "JsonSerializer" not in vars(_module)
        assert "StandardJsonSerializer" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_request_executor(self):
        assert "HttpRequestExecutor" not in vars(_module)

    def test_does_not_contain_api_key_literal(self):
        src = inspect.getsource(create_http_transport)
        assert "api_key" not in src
        assert "API_KEY" not in src
        assert "BYBIT_" not in src

    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
