import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_private_request_sender_factory as _module
from execution_gateway.bybit_demo_execution_gateway_factory import (
    create_bybit_demo_execution_gateway,
)
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_private_request_sender_factory import (
    create_bybit_private_request_sender,
)
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request import HttpRequest
from execution_gateway.http_request_executor import HttpRequestExecutor


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

def _make_http_request(url: str = "https://api-demo.bybit.com/v5/order/create") -> HttpRequest:
    return HttpRequest(url=url, headers={"Content-Type": "application/json"}, body="{}")


class SpyBuilder(BybitRequestBuilder):
    def __init__(self, result: HttpRequest | None = None):
        self.calls: list[dict] = []
        self._result = result or _make_http_request()

    def build(self, *, url: str, payload: object) -> HttpRequest:
        self.calls.append({"url": url, "payload": payload})
        return self._result


class SpyExecutor(HttpRequestExecutor):
    def __init__(self, result: str = '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'):
        self.calls: list[dict] = []
        self._result = result

    def execute(self, *, request: HttpRequest) -> str:
        self.calls.append({"request": request})
        return self._result


class RaisingExecutor(HttpRequestExecutor):
    def __init__(self, error: Exception):
        self._error = error
        self.call_count = 0

    def execute(self, *, request: HttpRequest) -> str:
        self.call_count += 1
        raise self._error


class SpySerializer:
    def __init__(self):
        self.dumps_calls: list = []
        self.loads_calls: list = []

    def dumps(self, value: object) -> str:
        self.dumps_calls.append(value)
        return "{}"

    def loads(self, value: str) -> object:
        self.loads_calls.append(value)
        return {"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": 1000}


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_private_request_sender_factory import (
            create_bybit_private_request_sender as f,
        )
        assert f is create_bybit_private_request_sender

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_private_request_sender")
        assert (
            execution_gateway.create_bybit_private_request_sender
            is create_bybit_private_request_sender
        )

    def test_included_in_all(self):
        assert "create_bybit_private_request_sender" in execution_gateway.__all__

    def test_single_factory_for_sender(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name))
            and "request_sender" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_private_request_sender"

    def test_positional_call_rejected(self):
        with pytest.raises(TypeError):
            create_bybit_private_request_sender(SpyBuilder(), SpyExecutor())

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_return_annotation_is_bybit_private_request_sender(self):
        hints = inspect.get_annotations(create_bybit_private_request_sender, eval_str=True)
        assert hints.get("return") is BybitPrivateRequestSender


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_request_builder_param(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "request_builder" in sig.parameters

    def test_has_request_executor_param(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "request_executor" in sig.parameters

    def test_exactly_two_params(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert len(sig.parameters) == 2

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "base_url" not in sig.parameters

    def test_does_not_receive_transport_directly(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert "transport" not in sig.parameters

    def test_no_default_for_request_builder(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert sig.parameters["request_builder"].default is inspect.Parameter.empty

    def test_no_default_for_request_executor(self):
        sig = inspect.signature(create_bybit_private_request_sender)
        assert sig.parameters["request_executor"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Validación — request_builder
# ---------------------------------------------------------------------------

class TestValidationRequestBuilder:
    def test_accepts_valid_builder(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert s is not None

    def test_rejects_none_builder(self):
        with pytest.raises(TypeError, match="request_builder must be BybitRequestBuilder"):
            create_bybit_private_request_sender(
                request_builder=None, request_executor=SpyExecutor()
            )

    def test_rejects_dict_builder(self):
        with pytest.raises(TypeError, match="request_builder must be BybitRequestBuilder"):
            create_bybit_private_request_sender(
                request_builder={"build": None}, request_executor=SpyExecutor()
            )

    def test_rejects_string_builder(self):
        with pytest.raises(TypeError, match="request_builder must be BybitRequestBuilder"):
            create_bybit_private_request_sender(
                request_builder="builder", request_executor=SpyExecutor()
            )

    def test_rejects_arbitrary_object_builder(self):
        with pytest.raises(TypeError, match="request_builder must be BybitRequestBuilder"):
            create_bybit_private_request_sender(
                request_builder=object(), request_executor=SpyExecutor()
            )

    def test_accepts_subclass_builder(self):
        class SubBuilder(SpyBuilder):
            pass
        s = create_bybit_private_request_sender(
            request_builder=SubBuilder(), request_executor=SpyExecutor()
        )
        assert isinstance(s, BybitPrivateRequestSender)

    def test_does_not_convert_builder(self):
        with pytest.raises(TypeError):
            create_bybit_private_request_sender(
                request_builder=None, request_executor=SpyExecutor()
            )


# ---------------------------------------------------------------------------
# 4. Validación — request_executor
# ---------------------------------------------------------------------------

class TestValidationRequestExecutor:
    def test_accepts_valid_executor(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert s is not None

    def test_rejects_none_executor(self):
        with pytest.raises(TypeError, match="request_executor must be HttpRequestExecutor"):
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor=None
            )

    def test_rejects_dict_executor(self):
        with pytest.raises(TypeError, match="request_executor must be HttpRequestExecutor"):
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor={"execute": None}
            )

    def test_rejects_string_executor(self):
        with pytest.raises(TypeError, match="request_executor must be HttpRequestExecutor"):
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor="executor"
            )

    def test_rejects_arbitrary_object_executor(self):
        with pytest.raises(TypeError, match="request_executor must be HttpRequestExecutor"):
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor=42
            )

    def test_accepts_subclass_executor(self):
        class SubExecutor(SpyExecutor):
            pass
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SubExecutor()
        )
        assert isinstance(s, BybitPrivateRequestSender)

    def test_does_not_convert_executor(self):
        with pytest.raises(TypeError):
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor=None
            )


# ---------------------------------------------------------------------------
# 5. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_private_request_sender(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert isinstance(s, BybitPrivateRequestSender)

    def test_returns_exact_type(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert type(s) is BybitPrivateRequestSender

    def test_two_calls_return_different_senders(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s1 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s2 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        assert s1 is not s2

    def test_does_not_return_builder(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert not isinstance(s, BybitRequestBuilder)

    def test_does_not_return_executor(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert not isinstance(s, HttpRequestExecutor)

    def test_does_not_return_tuple(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert not isinstance(s, tuple)

    def test_does_not_return_dict(self):
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert not isinstance(s, dict)


# ---------------------------------------------------------------------------
# 6. Grafo e identidad
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_request_builder_stored_by_identity(self):
        b = SpyBuilder()
        s = create_bybit_private_request_sender(
            request_builder=b, request_executor=SpyExecutor()
        )
        assert s._request_builder is b

    def test_request_executor_stored_by_identity(self):
        e = SpyExecutor()
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=e
        )
        assert s._request_executor is e

    def test_both_dependencies_stored(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        assert s._request_builder is b
        assert s._request_executor is e

    def test_does_not_wrap_builder(self):
        b = SpyBuilder()
        s = create_bybit_private_request_sender(
            request_builder=b, request_executor=SpyExecutor()
        )
        assert type(s._request_builder) is SpyBuilder

    def test_does_not_wrap_executor(self):
        e = SpyExecutor()
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=e
        )
        assert type(s._request_executor) is SpyExecutor


# ---------------------------------------------------------------------------
# 7. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_senders(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s1 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s2 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        assert s1 is not s2

    def test_builder_identity_preserved_across_calls(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s1 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s2 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        assert s1._request_builder is b
        assert s2._request_builder is b

    def test_executor_identity_preserved_across_calls(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s1 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s2 = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        assert s1._request_executor is e
        assert s2._request_executor is e

    def test_no_global_state_between_calls(self):
        b1, e1 = SpyBuilder(), SpyExecutor()
        b2, e2 = SpyBuilder(), SpyExecutor()
        s1 = create_bybit_private_request_sender(request_builder=b1, request_executor=e1)
        s2 = create_bybit_private_request_sender(request_builder=b2, request_executor=e2)
        assert s1._request_builder is b1
        assert s1._request_executor is e1
        assert s2._request_builder is b2
        assert s2._request_executor is e2


# ---------------------------------------------------------------------------
# 8. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_builder_not_called_during_construction(self):
        b = SpyBuilder()
        create_bybit_private_request_sender(request_builder=b, request_executor=SpyExecutor())
        assert b.calls == []

    def test_executor_not_called_during_construction(self):
        e = SpyExecutor()
        create_bybit_private_request_sender(request_builder=SpyBuilder(), request_executor=e)
        assert e.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_private_request_sender(
                request_builder=SpyBuilder(), request_executor=SpyExecutor()
            )
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        s = create_bybit_private_request_sender(
            request_builder=SpyBuilder(), request_executor=SpyExecutor()
        )
        assert isinstance(s, BybitPrivateRequestSender)


# ---------------------------------------------------------------------------
# 9. Comportamiento integrado mínimo del sender
# ---------------------------------------------------------------------------

class TestIntegratedSenderBehavior:
    def test_send_calls_builder_exactly_once(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload={"symbol": "BTCUSDT"})
        assert len(b.calls) == 1

    def test_send_passes_url_to_builder(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert b.calls[0]["url"] == "https://api-demo.bybit.com/v5/order/create"

    def test_send_passes_payload_to_builder(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        payload = {"symbol": "BTCUSDT", "side": "Buy"}
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload=payload)
        assert b.calls[0]["payload"] is payload

    def test_send_calls_executor_exactly_once(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert len(e.calls) == 1

    def test_send_passes_builder_result_to_executor(self):
        http_req = _make_http_request()
        b = SpyBuilder(result=http_req)
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert e.calls[0]["request"] is http_req

    def test_send_returns_executor_result(self):
        b = SpyBuilder()
        e = SpyExecutor(result="response-body-text")
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        result = s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert result == "response-body-text"

    def test_send_returns_str(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        result = s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert isinstance(result, str)

    def test_no_retry_on_success(self):
        b = SpyBuilder()
        e = SpyExecutor()
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert len(e.calls) == 1

    def test_transport_error_propagates_by_identity(self):
        transport_error = RuntimeError("connection refused")
        b = SpyBuilder()
        e = RaisingExecutor(error=transport_error)
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        with pytest.raises(RuntimeError) as exc_info:
            s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert exc_info.value is transport_error

    def test_no_retry_on_transport_error(self):
        b = SpyBuilder()
        e = RaisingExecutor(error=RuntimeError("fail"))
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        with pytest.raises(RuntimeError):
            s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert e.call_count == 1

    def test_no_fallback_on_transport_error(self):
        b = SpyBuilder()
        e = RaisingExecutor(error=RuntimeError("fail"))
        s = create_bybit_private_request_sender(request_builder=b, request_executor=e)
        with pytest.raises(RuntimeError):
            s.send(url="https://api-demo.bybit.com/v5/order/create", payload={})


# ---------------------------------------------------------------------------
# 10. Integración compositiva completa
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def _build_full_stack(self):
        spy_builder = SpyBuilder()
        spy_executor = SpyExecutor()
        spy_serializer = SpySerializer()
        sender = create_bybit_private_request_sender(
            request_builder=spy_builder,
            request_executor=spy_executor,
        )
        parser = create_bybit_response_parser(serializer=spy_serializer)
        api = create_bybit_private_api(sender=sender, response_parser=parser)
        gw = create_bybit_demo_execution_gateway(private_api=api)
        return gw, sender, parser, api, spy_builder, spy_executor, spy_serializer

    def test_gateway_builds_correctly(self):
        gw, *_ = self._build_full_stack()
        assert isinstance(gw, BybitExecutionGateway)

    def test_sender_identity_in_private_api(self):
        gw, sender, parser, api, *_ = self._build_full_stack()
        assert api._sender is sender

    def test_parser_identity_in_private_api(self):
        gw, sender, parser, api, *_ = self._build_full_stack()
        assert api._response_parser is parser

    def test_builder_identity_in_sender(self):
        gw, sender, parser, api, spy_builder, *_ = self._build_full_stack()
        assert sender._request_builder is spy_builder

    def test_executor_identity_in_sender(self):
        gw, sender, parser, api, spy_builder, spy_executor, *_ = self._build_full_stack()
        assert sender._request_executor is spy_executor

    def test_no_execution_during_full_composition(self):
        gw, sender, parser, api, spy_builder, spy_executor, spy_serializer = self._build_full_stack()
        assert spy_builder.calls == []
        assert spy_executor.calls == []
        assert spy_serializer.dumps_calls == []
        assert spy_serializer.loads_calls == []

    def test_private_api_identity_reachable_through_gateway(self):
        gw, sender, parser, api, *_ = self._build_full_stack()
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api is api

    def test_sender_identity_reachable_through_gateway(self):
        gw, sender, *_ = self._build_full_stack()
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api._sender is sender


# ---------------------------------------------------------------------------
# 11. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_private_request_sender)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_private_request_sender)
        assert "api_secret" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "HmacSha256Signer" not in vars(_module)
        assert "MessageSigner" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)

    def test_does_not_import_serializer(self):
        assert "StandardJsonSerializer" not in vars(_module)
        assert "JsonSerializer" not in vars(_module)
