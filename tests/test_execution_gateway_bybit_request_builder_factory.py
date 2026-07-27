import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_request_builder_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
from execution_gateway.bybit_demo_execution_gateway_factory import (
    create_bybit_demo_execution_gateway,
)
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import (
    create_bybit_private_request_sender,
)
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request import HttpRequest
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.json_serializer import JsonSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_auth(
    api_key: str = "test_key",
    signature: str = "abc123",
) -> BybitAuthentication:
    return BybitAuthentication(
        timestamp_ms=1_700_000_000_000,
        api_key=api_key,
        recv_window_ms=5_000,
        signature=signature,
    )


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpySerializer:
    def __init__(self, result: str = '{"symbol":"BTCUSDT"}'):
        self.dumps_calls: list = []
        self.loads_calls: list = []
        self._result = result

    def dumps(self, value: object) -> str:
        self.dumps_calls.append(value)
        return self._result

    def loads(self, value: str) -> object:
        self.loads_calls.append(value)
        return {}


class SpyAuthenticator:
    def __init__(self, result: BybitAuthentication | None = None):
        self.calls: list[dict] = []
        self._result = result or _make_auth()

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.calls.append({"body": body})
        return self._result


class RaisingAuthenticator:
    def __init__(self, error: Exception):
        self._error = error
        self.call_count = 0

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.call_count += 1
        raise self._error


class SpyHeaderBuilder(BybitHeaderBuilder):
    def __init__(self):
        self.calls: list[dict] = []

    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        self.calls.append({"authentication": authentication})
        return super().build(authentication=authentication)


class SpyExecutor(HttpRequestExecutor):
    def __init__(self):
        self.calls: list[dict] = []

    def execute(self, *, request: HttpRequest) -> str:
        self.calls.append({"request": request})
        return '{"retCode":0,"retMsg":"OK","result":{},"retExtInfo":{},"time":1000}'


class SpyParserSerializer:
    def dumps(self, v):
        return "{}"

    def loads(self, v):
        return {"retCode": 0, "retMsg": "OK", "result": {}, "retExtInfo": {}, "time": 1000}


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_request_builder_factory import (
            create_bybit_request_builder as f,
        )
        assert f is create_bybit_request_builder

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_request_builder")
        assert execution_gateway.create_bybit_request_builder is create_bybit_request_builder

    def test_included_in_all(self):
        assert "create_bybit_request_builder" in execution_gateway.__all__

    def test_single_factory_for_bybit_request_builder(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name))
            and "request_builder" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_request_builder"

    def test_positional_call_rejected(self):
        with pytest.raises(TypeError):
            create_bybit_request_builder(
                SpySerializer(), SpyAuthenticator(), SpyHeaderBuilder()
            )

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_bybit_request_builder)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_return_annotation_is_bybit_request_builder(self):
        hints = inspect.get_annotations(create_bybit_request_builder, eval_str=True)
        assert hints.get("return") is BybitRequestBuilder


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_serializer_param(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "serializer" in sig.parameters

    def test_has_authenticator_param(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "authenticator" in sig.parameters

    def test_has_header_builder_param(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "header_builder" in sig.parameters

    def test_exactly_three_params(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert len(sig.parameters) == 3

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_transport(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "transport" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert "base_url" not in sig.parameters

    def test_no_default_for_serializer(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert sig.parameters["serializer"].default is inspect.Parameter.empty

    def test_no_default_for_authenticator(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert sig.parameters["authenticator"].default is inspect.Parameter.empty

    def test_no_default_for_header_builder(self):
        sig = inspect.signature(create_bybit_request_builder)
        assert sig.parameters["header_builder"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Validación — serializer
# ---------------------------------------------------------------------------

class TestValidationSerializer:
    def test_accepts_valid_serializer(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert b is not None

    def test_accepts_structural_serializer(self):
        class AnonSerializer:
            def dumps(self, v): return "{}"
            def loads(self, v): return {}
        b = create_bybit_request_builder(
            serializer=AnonSerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert isinstance(b, BybitRequestBuilder)

    def test_rejects_none_serializer(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_request_builder(
                serializer=None,
                authenticator=SpyAuthenticator(),
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_dict_serializer(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_request_builder(
                serializer={"dumps": None},
                authenticator=SpyAuthenticator(),
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_string_serializer(self):
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_request_builder(
                serializer="json",
                authenticator=SpyAuthenticator(),
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_object_without_loads(self):
        class NoDumps:
            def loads(self, v): return {}
        with pytest.raises(TypeError, match="JsonSerializer"):
            create_bybit_request_builder(
                serializer=NoDumps(),
                authenticator=SpyAuthenticator(),
                header_builder=SpyHeaderBuilder(),
            )


# ---------------------------------------------------------------------------
# 4. Validación — authenticator
# ---------------------------------------------------------------------------

class TestValidationAuthenticator:
    def test_accepts_valid_authenticator(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert b is not None

    def test_accepts_structural_authenticator(self):
        class AnonAuth:
            def authenticate(self, *, body: str) -> BybitAuthentication:
                return _make_auth()
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=AnonAuth(),
            header_builder=SpyHeaderBuilder(),
        )
        assert isinstance(b, BybitRequestBuilder)

    def test_rejects_none_authenticator(self):
        with pytest.raises(TypeError, match="BybitAuthenticator"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=None,
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_dict_authenticator(self):
        with pytest.raises(TypeError, match="BybitAuthenticator"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator={"authenticate": None},
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_string_authenticator(self):
        with pytest.raises(TypeError, match="BybitAuthenticator"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator="auth",
                header_builder=SpyHeaderBuilder(),
            )

    def test_rejects_object_without_authenticate(self):
        with pytest.raises(TypeError, match="BybitAuthenticator"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=object(),
                header_builder=SpyHeaderBuilder(),
            )


# ---------------------------------------------------------------------------
# 5. Validación — header_builder
# ---------------------------------------------------------------------------

class TestValidationHeaderBuilder:
    def test_accepts_valid_header_builder(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert b is not None

    def test_accepts_bybit_header_builder_instance(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=BybitHeaderBuilder(),
        )
        assert isinstance(b, BybitRequestBuilder)

    def test_rejects_none_header_builder(self):
        with pytest.raises(TypeError, match="header_builder must be BybitHeaderBuilder"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=SpyAuthenticator(),
                header_builder=None,
            )

    def test_rejects_dict_header_builder(self):
        with pytest.raises(TypeError, match="header_builder must be BybitHeaderBuilder"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=SpyAuthenticator(),
                header_builder={"build": None},
            )

    def test_rejects_string_header_builder(self):
        with pytest.raises(TypeError, match="header_builder must be BybitHeaderBuilder"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=SpyAuthenticator(),
                header_builder="header",
            )

    def test_rejects_arbitrary_object(self):
        with pytest.raises(TypeError, match="header_builder must be BybitHeaderBuilder"):
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=SpyAuthenticator(),
                header_builder=object(),
            )

    def test_accepts_subclass(self):
        class SubHeader(SpyHeaderBuilder):
            pass
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SubHeader(),
        )
        assert isinstance(b, BybitRequestBuilder)


# ---------------------------------------------------------------------------
# 6. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_request_builder(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert isinstance(b, BybitRequestBuilder)

    def test_returns_exact_type(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert type(b) is BybitRequestBuilder

    def test_two_calls_return_different_builders(self):
        s = SpySerializer()
        a = SpyAuthenticator()
        h = SpyHeaderBuilder()
        b1 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        b2 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        assert b1 is not b2

    def test_does_not_return_authenticator(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert not hasattr(b, "authenticate")

    def test_does_not_return_tuple(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert not isinstance(b, tuple)

    def test_does_not_return_dict(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert not isinstance(b, dict)


# ---------------------------------------------------------------------------
# 7. Grafo e identidad
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_serializer_stored_by_identity(self):
        s = SpySerializer()
        b = create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        assert b._serializer is s

    def test_authenticator_stored_by_identity(self):
        a = SpyAuthenticator()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=a, header_builder=SpyHeaderBuilder()
        )
        assert b._authenticator is a

    def test_header_builder_stored_by_identity(self):
        h = SpyHeaderBuilder()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=SpyAuthenticator(), header_builder=h
        )
        assert b._header_builder is h

    def test_all_dependencies_stored(self):
        s = SpySerializer()
        a = SpyAuthenticator()
        h = SpyHeaderBuilder()
        b = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        assert b._serializer is s
        assert b._authenticator is a
        assert b._header_builder is h

    def test_does_not_wrap_serializer(self):
        s = SpySerializer()
        b = create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        assert type(b._serializer) is SpySerializer

    def test_does_not_wrap_authenticator(self):
        a = SpyAuthenticator()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=a, header_builder=SpyHeaderBuilder()
        )
        assert type(b._authenticator) is SpyAuthenticator


# ---------------------------------------------------------------------------
# 8. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_builders(self):
        s = SpySerializer()
        a = SpyAuthenticator()
        h = SpyHeaderBuilder()
        b1 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        b2 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        assert b1 is not b2

    def test_serializer_identity_preserved_across_calls(self):
        s = SpySerializer()
        a = SpyAuthenticator()
        h = SpyHeaderBuilder()
        b1 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        b2 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        assert b1._serializer is s
        assert b2._serializer is s

    def test_authenticator_identity_preserved_across_calls(self):
        s = SpySerializer()
        a = SpyAuthenticator()
        h = SpyHeaderBuilder()
        b1 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        b2 = create_bybit_request_builder(serializer=s, authenticator=a, header_builder=h)
        assert b1._authenticator is a
        assert b2._authenticator is a

    def test_no_global_state_between_calls(self):
        s1, a1, h1 = SpySerializer(), SpyAuthenticator(), SpyHeaderBuilder()
        s2, a2, h2 = SpySerializer(), SpyAuthenticator(), SpyHeaderBuilder()
        b1 = create_bybit_request_builder(serializer=s1, authenticator=a1, header_builder=h1)
        b2 = create_bybit_request_builder(serializer=s2, authenticator=a2, header_builder=h2)
        assert b1._serializer is s1 and b1._authenticator is a1
        assert b2._serializer is s2 and b2._authenticator is a2


# ---------------------------------------------------------------------------
# 9. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_serializer_not_called_during_construction(self):
        s = SpySerializer()
        create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        assert s.dumps_calls == [] and s.loads_calls == []

    def test_authenticator_not_called_during_construction(self):
        a = SpyAuthenticator()
        create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=a, header_builder=SpyHeaderBuilder()
        )
        assert a.calls == []

    def test_header_builder_not_called_during_construction(self):
        h = SpyHeaderBuilder()
        create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=SpyAuthenticator(), header_builder=h
        )
        assert h.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_request_builder(
                serializer=SpySerializer(),
                authenticator=SpyAuthenticator(),
                header_builder=SpyHeaderBuilder(),
            )
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert isinstance(b, BybitRequestBuilder)


# ---------------------------------------------------------------------------
# 10. Comportamiento integrado mínimo del builder
# ---------------------------------------------------------------------------

class TestIntegratedBuilderBehavior:
    def test_build_returns_http_request(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        result = b.build(url="https://api-demo.bybit.com/v5/order/create", payload={"k": "v"})
        assert isinstance(result, HttpRequest)

    def test_build_serializes_payload_exactly_once(self):
        s = SpySerializer()
        b = create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload={"symbol": "BTCUSDT"})
        assert len(s.dumps_calls) == 1

    def test_build_passes_payload_to_serializer(self):
        s = SpySerializer()
        b = create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        payload = {"symbol": "BTCUSDT", "side": "Buy"}
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload=payload)
        assert s.dumps_calls[0] is payload

    def test_build_authenticates_exactly_once(self):
        a = SpyAuthenticator()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=a, header_builder=SpyHeaderBuilder()
        )
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert len(a.calls) == 1

    def test_build_passes_serialized_body_to_authenticator(self):
        s = SpySerializer(result='{"serialized":"body"}')
        a = SpyAuthenticator()
        b = create_bybit_request_builder(
            serializer=s, authenticator=a, header_builder=SpyHeaderBuilder()
        )
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert a.calls[0]["body"] == '{"serialized":"body"}'

    def test_build_calls_header_builder_exactly_once(self):
        h = SpyHeaderBuilder()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=SpyAuthenticator(), header_builder=h
        )
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert len(h.calls) == 1

    def test_build_passes_auth_result_to_header_builder(self):
        auth_result = _make_auth(api_key="mykey", signature="mysig")
        a = SpyAuthenticator(result=auth_result)
        h = SpyHeaderBuilder()
        b = create_bybit_request_builder(
            serializer=SpySerializer(), authenticator=a, header_builder=h
        )
        b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert h.calls[0]["authentication"] is auth_result

    def test_build_conserves_url_in_request(self):
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        url = "https://api-demo.bybit.com/v5/order/create"
        result = b.build(url=url, payload={})
        assert result.url == url

    def test_build_conserves_body_in_request(self):
        s = SpySerializer(result='{"body":"content"}')
        b = create_bybit_request_builder(
            serializer=s, authenticator=SpyAuthenticator(), header_builder=SpyHeaderBuilder()
        )
        result = b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert result.body == '{"body":"content"}'

    def test_build_headers_contain_api_key(self):
        auth = _make_auth(api_key="myapikey")
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=SpyAuthenticator(result=auth),
            header_builder=BybitHeaderBuilder(),
        )
        result = b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert result.headers.get("X-BAPI-API-KEY") == "myapikey"

    def test_authentication_error_propagates_by_identity(self):
        auth_error = ValueError("auth failed")
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=RaisingAuthenticator(error=auth_error),
            header_builder=SpyHeaderBuilder(),
        )
        with pytest.raises(ValueError) as exc_info:
            b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert exc_info.value is auth_error

    def test_no_retry_on_authentication_error(self):
        raising = RaisingAuthenticator(error=RuntimeError("fail"))
        b = create_bybit_request_builder(
            serializer=SpySerializer(),
            authenticator=raising,
            header_builder=SpyHeaderBuilder(),
        )
        with pytest.raises(RuntimeError):
            b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert raising.call_count == 1

    def test_no_retry_after_error(self):
        s = SpySerializer()
        raising = RaisingAuthenticator(error=RuntimeError("fail"))
        b = create_bybit_request_builder(
            serializer=s, authenticator=raising, header_builder=SpyHeaderBuilder()
        )
        with pytest.raises(RuntimeError):
            b.build(url="https://api-demo.bybit.com/v5/order/create", payload={})
        assert len(s.dumps_calls) == 1


# ---------------------------------------------------------------------------
# 11. Integración compositiva completa
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def _build_full_stack(self):
        spy_serializer = SpySerializer()
        spy_authenticator = SpyAuthenticator()
        spy_header_builder = SpyHeaderBuilder()
        spy_executor = SpyExecutor()
        spy_parser_serializer = SpyParserSerializer()

        request_builder = create_bybit_request_builder(
            serializer=spy_serializer,
            authenticator=spy_authenticator,
            header_builder=spy_header_builder,
        )
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=spy_executor,
        )
        parser = create_bybit_response_parser(serializer=spy_parser_serializer)
        api = create_bybit_private_api(sender=sender, response_parser=parser)
        gw = create_bybit_demo_execution_gateway(private_api=api)
        return gw, request_builder, sender, parser, api, spy_serializer, spy_authenticator, spy_header_builder, spy_executor

    def test_gateway_builds_correctly(self):
        gw, *_ = self._build_full_stack()
        assert isinstance(gw, BybitExecutionGateway)

    def test_builder_identity_in_sender(self):
        gw, request_builder, sender, *_ = self._build_full_stack()
        assert sender._request_builder is request_builder

    def test_sender_identity_in_private_api(self):
        gw, _, sender, parser, api, *_ = self._build_full_stack()
        assert api._sender is sender

    def test_parser_identity_in_private_api(self):
        gw, _, sender, parser, api, *_ = self._build_full_stack()
        assert api._response_parser is parser

    def test_serializer_identity_in_builder(self):
        gw, request_builder, _, _, _, spy_serializer, *_ = self._build_full_stack()
        assert request_builder._serializer is spy_serializer

    def test_authenticator_identity_in_builder(self):
        gw, request_builder, _, _, _, _, spy_authenticator, *_ = self._build_full_stack()
        assert request_builder._authenticator is spy_authenticator

    def test_no_execution_during_full_composition(self):
        gw, _, _, _, _, spy_serializer, spy_authenticator, spy_header_builder, spy_executor = self._build_full_stack()
        assert spy_serializer.dumps_calls == []
        assert spy_authenticator.calls == []
        assert spy_header_builder.calls == []
        assert spy_executor.calls == []

    def test_builder_identity_reachable_through_gateway(self):
        gw, request_builder, *_ = self._build_full_stack()
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api._sender._request_builder is request_builder


# ---------------------------------------------------------------------------
# 12. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_request_builder)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_request_builder)
        assert "api_secret" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "HmacSha256Signer" not in vars(_module)
        assert "MessageSigner" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)

    def test_does_not_import_standard_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_standard_serializer(self):
        assert "StandardJsonSerializer" not in vars(_module)
