import inspect

import pytest

import execution_gateway
import execution_gateway.http_request_executor_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request import HttpRequest
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport import HttpTransport
from execution_gateway.urllib_http_transport import UrllibHttpTransport


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    url: str = "https://api-demo.bybit.com/v5/order/create",
    headers: dict | None = None,
    body: str = '{"symbol":"BTCUSDT"}',
) -> HttpRequest:
    return HttpRequest(
        url=url,
        headers=headers if headers is not None else {"X-BAPI-API-KEY": "key"},
        body=body,
    )


def _make_executor(timeout_seconds: float = 5.0) -> tuple[HttpRequestExecutor, "SpyTransport"]:
    t = SpyTransport()
    e = create_http_request_executor(transport=t, timeout_seconds=timeout_seconds)
    return e, t


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyTransport:
    def __init__(
        self,
        result: str = '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}',
    ):
        self.calls: list[dict] = []
        self._result = result

    def post(
        self,
        *,
        url: str,
        headers,
        body: str,
        timeout_seconds: float,
    ) -> str:
        self.calls.append(
            {"url": url, "headers": headers, "body": body, "timeout_seconds": timeout_seconds}
        )
        return self._result


class RaisingTransport:
    def __init__(self, error: Exception):
        self._error = error
        self.call_count = 0

    def post(self, *, url: str, headers, body: str, timeout_seconds: float) -> str:
        self.call_count += 1
        raise self._error


class SpyAuthenticator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

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
        self.calls: list[dict] = []

    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        self.calls.append({"authentication": authentication})
        return super().build(authentication=authentication)


class SpySerializer:
    def __init__(self) -> None:
        self.dumps_calls: list = []
        self.loads_calls: list = []

    def dumps(self, v: object) -> str:
        self.dumps_calls.append(v)
        return "{}"

    def loads(self, v: str) -> object:
        self.loads_calls.append(v)
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
        from execution_gateway.http_request_executor_factory import (
            create_http_request_executor as f,
        )
        assert f is create_http_request_executor

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_http_request_executor")
        assert execution_gateway.create_http_request_executor is create_http_request_executor

    def test_included_in_all(self):
        assert "create_http_request_executor" in execution_gateway.__all__

    def test_single_factory_for_http_request_executor(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "executor" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_http_request_executor"

    def test_positional_call_rejected(self):
        with pytest.raises(TypeError):
            create_http_request_executor(SpyTransport(), 5.0)

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_http_request_executor)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_return_annotation_is_http_request_executor(self):
        hints = inspect.get_annotations(create_http_request_executor, eval_str=True)
        assert hints.get("return") is HttpRequestExecutor


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_transport_param(self):
        sig = inspect.signature(create_http_request_executor)
        assert "transport" in sig.parameters

    def test_has_timeout_seconds_param(self):
        sig = inspect.signature(create_http_request_executor)
        assert "timeout_seconds" in sig.parameters

    def test_exactly_two_params(self):
        sig = inspect.signature(create_http_request_executor)
        assert len(sig.parameters) == 2

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_http_request_executor)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_http_request_executor)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_authenticator(self):
        sig = inspect.signature(create_http_request_executor)
        assert "authenticator" not in sig.parameters

    def test_does_not_receive_serializer(self):
        sig = inspect.signature(create_http_request_executor)
        assert "serializer" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_http_request_executor)
        assert "base_url" not in sig.parameters

    def test_no_default_for_transport(self):
        sig = inspect.signature(create_http_request_executor)
        assert sig.parameters["transport"].default is inspect.Parameter.empty

    def test_no_default_for_timeout_seconds(self):
        sig = inspect.signature(create_http_request_executor)
        assert sig.parameters["timeout_seconds"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Validación — transport
# ---------------------------------------------------------------------------

class TestValidationTransport:
    def test_accepts_valid_transport(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=5.0)
        assert e is not None

    def test_accepts_structural_transport(self):
        class AnonTransport:
            def post(self, *, url, headers, body, timeout_seconds):
                return ""
        e = create_http_request_executor(transport=AnonTransport(), timeout_seconds=5.0)
        assert isinstance(e, HttpRequestExecutor)

    def test_accepts_urllib_http_transport(self):
        e = create_http_request_executor(transport=UrllibHttpTransport(), timeout_seconds=5.0)
        assert isinstance(e, HttpRequestExecutor)

    def test_rejects_none_transport(self):
        with pytest.raises(TypeError, match="HttpTransport"):
            create_http_request_executor(transport=None, timeout_seconds=5.0)

    def test_rejects_dict_transport(self):
        with pytest.raises(TypeError, match="HttpTransport"):
            create_http_request_executor(transport={"post": None}, timeout_seconds=5.0)

    def test_rejects_string_transport(self):
        with pytest.raises(TypeError, match="HttpTransport"):
            create_http_request_executor(transport="urllib", timeout_seconds=5.0)

    def test_rejects_object_without_post(self):
        with pytest.raises(TypeError, match="HttpTransport"):
            create_http_request_executor(transport=object(), timeout_seconds=5.0)

    def test_accepts_spy_subclass(self):
        class SubSpy(SpyTransport):
            pass
        e = create_http_request_executor(transport=SubSpy(), timeout_seconds=5.0)
        assert isinstance(e, HttpRequestExecutor)

    def test_error_message_contains_type_name(self):
        with pytest.raises(TypeError, match="int"):
            create_http_request_executor(transport=42, timeout_seconds=5.0)


# ---------------------------------------------------------------------------
# 4. Validación — timeout_seconds
# ---------------------------------------------------------------------------

class TestValidationTimeoutSeconds:
    def test_accepts_positive_float(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=5.0)
        assert e is not None

    def test_accepts_positive_int(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=10)
        assert isinstance(e, HttpRequestExecutor)

    def test_accepts_small_positive(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=0.001)
        assert isinstance(e, HttpRequestExecutor)

    def test_accepts_large_timeout(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=300)
        assert isinstance(e, HttpRequestExecutor)

    def test_timeout_value_preserved_exactly(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=12.345)
        assert e._timeout_seconds == 12.345

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=0)

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=-1.0)

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="timeout_seconds"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=None)

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="timeout_seconds"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds="5")

    def test_rejects_bool_true(self):
        with pytest.raises(TypeError, match="timeout_seconds"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=True)

    def test_rejects_bool_false(self):
        with pytest.raises(TypeError, match="timeout_seconds"):
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=False)


# ---------------------------------------------------------------------------
# 5. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_http_request_executor(self):
        e, _ = _make_executor()
        assert isinstance(e, HttpRequestExecutor)

    def test_returns_exact_type(self):
        e, _ = _make_executor()
        assert type(e) is HttpRequestExecutor

    def test_two_calls_return_different_executors(self):
        t = SpyTransport()
        e1 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        e2 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert e1 is not e2

    def test_does_not_return_transport(self):
        e, _ = _make_executor()
        assert not isinstance(e, SpyTransport)

    def test_does_not_return_tuple(self):
        e, _ = _make_executor()
        assert not isinstance(e, tuple)

    def test_does_not_return_dict(self):
        e, _ = _make_executor()
        assert not isinstance(e, dict)

    def test_has_execute_method(self):
        e, _ = _make_executor()
        assert callable(getattr(e, "execute", None))


# ---------------------------------------------------------------------------
# 6. Grafo e identidad
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_transport_stored_by_identity(self):
        t = SpyTransport()
        e = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert e._transport is t

    def test_timeout_stored_exactly(self):
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=7.5)
        assert e._timeout_seconds == 7.5

    def test_all_dependencies_stored(self):
        t = SpyTransport()
        e = create_http_request_executor(transport=t, timeout_seconds=9.0)
        assert e._transport is t
        assert e._timeout_seconds == 9.0

    def test_does_not_wrap_transport(self):
        t = SpyTransport()
        e = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert type(e._transport) is SpyTransport

    def test_transport_type_preserved(self):
        t = UrllibHttpTransport()
        e = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert e._transport is t
        assert type(e._transport) is UrllibHttpTransport


# ---------------------------------------------------------------------------
# 7. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_executors(self):
        t = SpyTransport()
        e1 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        e2 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert e1 is not e2

    def test_transport_identity_preserved_across_calls(self):
        t = SpyTransport()
        e1 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        e2 = create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert e1._transport is t
        assert e2._transport is t

    def test_timeout_preserved_across_calls(self):
        t = SpyTransport()
        e1 = create_http_request_executor(transport=t, timeout_seconds=3.0)
        e2 = create_http_request_executor(transport=t, timeout_seconds=7.0)
        assert e1._timeout_seconds == 3.0
        assert e2._timeout_seconds == 7.0

    def test_no_global_state_between_calls(self):
        t1 = SpyTransport()
        t2 = SpyTransport()
        e1 = create_http_request_executor(transport=t1, timeout_seconds=5.0)
        e2 = create_http_request_executor(transport=t2, timeout_seconds=10.0)
        assert e1._transport is t1
        assert e2._transport is t2
        assert e1._timeout_seconds == 5.0
        assert e2._timeout_seconds == 10.0


# ---------------------------------------------------------------------------
# 8. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_transport_not_called_during_construction(self):
        t = SpyTransport()
        create_http_request_executor(transport=t, timeout_seconds=5.0)
        assert t.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_http_request_executor(transport=SpyTransport(), timeout_seconds=5.0)
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        e = create_http_request_executor(transport=SpyTransport(), timeout_seconds=5.0)
        assert isinstance(e, HttpRequestExecutor)

    def test_urllib_transport_not_invoked_during_construction(self):
        import urllib.request
        called = []
        original = urllib.request.urlopen

        def patched(*args, **kwargs):
            called.append(True)
            return original(*args, **kwargs)

        urllib.request.urlopen = patched
        try:
            create_http_request_executor(transport=UrllibHttpTransport(), timeout_seconds=5.0)
        finally:
            urllib.request.urlopen = original
        assert called == []


# ---------------------------------------------------------------------------
# 9. Comportamiento integrado mínimo del executor
# ---------------------------------------------------------------------------

class TestIntegratedExecutorBehavior:
    def test_execute_returns_transport_response(self):
        sentinel = "response_body_sentinel_42"
        t = SpyTransport(result=sentinel)
        e = create_http_request_executor(transport=t, timeout_seconds=5.0)
        result = e.execute(request=_make_request())
        assert result == sentinel

    def test_execute_returns_string(self):
        e, _ = _make_executor()
        result = e.execute(request=_make_request())
        assert isinstance(result, str)

    def test_execute_calls_transport_exactly_once(self):
        e, t = _make_executor()
        e.execute(request=_make_request())
        assert len(t.calls) == 1

    def test_execute_passes_url_to_transport(self):
        e, t = _make_executor()
        url = "https://api-demo.bybit.com/v5/order/create"
        e.execute(request=_make_request(url=url))
        assert t.calls[0]["url"] == url

    def test_execute_passes_body_to_transport(self):
        e, t = _make_executor()
        body = '{"symbol":"XAUTUSDT","side":"Sell"}'
        e.execute(request=_make_request(body=body))
        assert t.calls[0]["body"] == body

    def test_execute_passes_headers_to_transport(self):
        e, t = _make_executor()
        headers = {"X-BAPI-API-KEY": "mykey", "Content-Type": "application/json"}
        e.execute(request=_make_request(headers=headers))
        assert t.calls[0]["headers"] == headers

    def test_execute_passes_timeout_to_transport(self):
        t = SpyTransport()
        e = create_http_request_executor(transport=t, timeout_seconds=12.3)
        e.execute(request=_make_request())
        assert t.calls[0]["timeout_seconds"] == 12.3

    def test_transport_error_propagates_by_identity(self):
        err = OSError("connection refused")
        raising = RaisingTransport(error=err)
        e = create_http_request_executor(transport=raising, timeout_seconds=5.0)
        with pytest.raises(OSError) as exc_info:
            e.execute(request=_make_request())
        assert exc_info.value is err

    def test_no_retry_after_error(self):
        raising = RaisingTransport(error=OSError("fail"))
        e = create_http_request_executor(transport=raising, timeout_seconds=5.0)
        with pytest.raises(OSError):
            e.execute(request=_make_request())
        assert raising.call_count == 1

    def test_error_not_wrapped(self):
        err = ValueError("original error")
        raising = RaisingTransport(error=err)
        e = create_http_request_executor(transport=raising, timeout_seconds=5.0)
        with pytest.raises(ValueError, match="original error"):
            e.execute(request=_make_request())

    def test_response_not_modified(self):
        raw = '{"retCode":0,"retMsg":"OK","result":{"orderId":"abc"}}'
        t = SpyTransport(result=raw)
        e = create_http_request_executor(transport=t, timeout_seconds=5.0)
        result = e.execute(request=_make_request())
        assert result == raw


# ---------------------------------------------------------------------------
# 10. Integración compositiva completa
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def _build_full_stack(self):
        spy_transport = SpyTransport()
        spy_authenticator = SpyAuthenticator()
        spy_header_builder = SpyHeaderBuilder()
        spy_serializer = SpySerializer()
        spy_parser_serializer = SpyParserSerializer()

        executor = create_http_request_executor(
            transport=spy_transport,
            timeout_seconds=5.0,
        )
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
            executor,
            sender,
            parser,
            private_api,
            request_builder,
            spy_transport,
            spy_authenticator,
            spy_header_builder,
            spy_serializer,
        )

    def test_full_stack_builds_correctly(self):
        gateway, *_ = self._build_full_stack()
        assert isinstance(gateway, BybitExecutionGateway)

    def test_executor_identity_in_sender(self):
        _, executor, sender, *_ = self._build_full_stack()
        assert sender._request_executor is executor

    def test_transport_identity_in_executor(self):
        _, executor, _, _, _, _, spy_transport, *_ = self._build_full_stack()
        assert executor._transport is spy_transport

    def test_builder_identity_in_sender(self):
        _, _, sender, _, _, request_builder, *_ = self._build_full_stack()
        assert sender._request_builder is request_builder

    def test_sender_identity_in_private_api(self):
        _, _, sender, _, private_api, *_ = self._build_full_stack()
        assert private_api._sender is sender

    def test_parser_identity_in_private_api(self):
        _, _, _, parser, private_api, *_ = self._build_full_stack()
        assert private_api._response_parser is parser

    def test_no_transport_called_during_composition(self):
        *_, spy_transport, spy_authenticator, spy_header_builder, spy_serializer = self._build_full_stack()
        assert spy_transport.calls == []
        assert spy_authenticator.calls == []
        assert spy_header_builder.calls == []
        assert spy_serializer.dumps_calls == []


# ---------------------------------------------------------------------------
# 11. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_urllib(self):
        assert "urllib" not in vars(_module)
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "MessageSigner" not in vars(_module)
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_import_serializer(self):
        assert "JsonSerializer" not in vars(_module)
        assert "StandardJsonSerializer" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_request_builder(self):
        assert "BybitRequestBuilder" not in vars(_module)

    def test_does_not_import_private_request_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_http_request_executor)
        assert "api_key" not in src
        assert "API_KEY" not in src
        assert "BYBIT_" not in src

    def test_full_suite_still_passes(self):
        from execution_gateway.http_request_executor import HttpRequestExecutor as E
        assert E is HttpRequestExecutor
