import inspect
import json

import pytest

import execution_gateway
import execution_gateway.json_serializer_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer import JsonSerializer
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.standard_json_serializer import StandardJsonSerializer


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.json_serializer_factory import create_json_serializer as f
        assert f is create_json_serializer

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_json_serializer")
        assert execution_gateway.create_json_serializer is create_json_serializer

    def test_included_in_all(self):
        assert "create_json_serializer" in execution_gateway.__all__

    def test_single_factory_for_json_serializer(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "serializer" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_json_serializer"

    def test_callable(self):
        assert callable(create_json_serializer)

    def test_no_extra_args_accepted(self):
        with pytest.raises(TypeError):
            create_json_serializer(object())

    def test_return_annotation_is_standard_json_serializer(self):
        hints = inspect.get_annotations(create_json_serializer, eval_str=True)
        assert hints.get("return") is StandardJsonSerializer


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_zero_parameters(self):
        sig = inspect.signature(create_json_serializer)
        assert len(sig.parameters) == 0

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_json_serializer)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_json_serializer)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_transport(self):
        sig = inspect.signature(create_json_serializer)
        assert "transport" not in sig.parameters

    def test_does_not_receive_separators(self):
        sig = inspect.signature(create_json_serializer)
        assert "separators" not in sig.parameters

    def test_does_not_receive_indent(self):
        sig = inspect.signature(create_json_serializer)
        assert "indent" not in sig.parameters

    def test_does_not_receive_sort_keys(self):
        sig = inspect.signature(create_json_serializer)
        assert "sort_keys" not in sig.parameters

    def test_does_not_receive_encoding(self):
        sig = inspect.signature(create_json_serializer)
        assert "encoding" not in sig.parameters


# ---------------------------------------------------------------------------
# 3. Implementación concreta
# ---------------------------------------------------------------------------

class TestConcreteImplementation:
    def test_returns_standard_json_serializer(self):
        s = create_json_serializer()
        assert isinstance(s, StandardJsonSerializer)

    def test_returns_exact_type(self):
        s = create_json_serializer()
        assert type(s) is StandardJsonSerializer

    def test_satisfies_json_serializer_protocol(self):
        s = create_json_serializer()
        assert isinstance(s, JsonSerializer)

    def test_not_the_protocol(self):
        s = create_json_serializer()
        assert type(s) is not JsonSerializer

    def test_has_dumps_method(self):
        s = create_json_serializer()
        assert callable(getattr(s, "dumps", None))

    def test_has_loads_method(self):
        s = create_json_serializer()
        assert callable(getattr(s, "loads", None))


# ---------------------------------------------------------------------------
# 4. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_new_instance_per_call(self):
        s1 = create_json_serializer()
        s2 = create_json_serializer()
        assert s1 is not s2

    def test_multiple_instances_all_distinct(self):
        instances = [create_json_serializer() for _ in range(4)]
        ids = [id(s) for s in instances]
        assert len(set(ids)) == 4

    def test_does_not_return_tuple(self):
        s = create_json_serializer()
        assert not isinstance(s, tuple)

    def test_does_not_return_dict(self):
        s = create_json_serializer()
        assert not isinstance(s, dict)

    def test_does_not_return_none(self):
        s = create_json_serializer()
        assert s is not None

    def test_does_not_return_class(self):
        s = create_json_serializer()
        assert not inspect.isclass(s)


# ---------------------------------------------------------------------------
# 5. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_no_singleton_behavior(self):
        s1 = create_json_serializer()
        s2 = create_json_serializer()
        assert s1 is not s2

    def test_each_is_standard_json_serializer(self):
        for _ in range(3):
            s = create_json_serializer()
            assert type(s) is StandardJsonSerializer

    def test_no_shared_state(self):
        s1 = create_json_serializer()
        s2 = create_json_serializer()
        assert s1 is not s2
        assert type(s1) is type(s2)


# ---------------------------------------------------------------------------
# 6. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_dumps_not_called_during_construction(self, monkeypatch):
        calls = []
        original_dumps = json.dumps
        monkeypatch.setattr(json, "dumps", lambda *a, **kw: calls.append(a) or original_dumps(*a, **kw))
        create_json_serializer()
        assert calls == []

    def test_loads_not_called_during_construction(self, monkeypatch):
        calls = []
        original_loads = json.loads
        monkeypatch.setattr(json, "loads", lambda *a, **kw: calls.append(a) or original_loads(*a, **kw))
        create_json_serializer()
        assert calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        s = create_json_serializer()
        assert isinstance(s, StandardJsonSerializer)

    def test_no_network_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_json_serializer()
        finally:
            socket.socket.connect = original
        assert network_calls == []


# ---------------------------------------------------------------------------
# 7. Comportamiento integrado mínimo del serializer
# ---------------------------------------------------------------------------

class TestIntegratedSerializerBehavior:
    def test_dumps_dict(self):
        s = create_json_serializer()
        assert s.dumps({"a": 1}) == json.dumps({"a": 1})

    def test_dumps_string(self):
        s = create_json_serializer()
        assert s.dumps("hello") == json.dumps("hello")

    def test_dumps_list(self):
        s = create_json_serializer()
        assert s.dumps([1, 2, 3]) == json.dumps([1, 2, 3])

    def test_dumps_bool_true(self):
        s = create_json_serializer()
        assert s.dumps(True) == "true"

    def test_dumps_bool_false(self):
        s = create_json_serializer()
        assert s.dumps(False) == "false"

    def test_dumps_null(self):
        s = create_json_serializer()
        assert s.dumps(None) == "null"

    def test_dumps_number(self):
        s = create_json_serializer()
        assert s.dumps(42) == "42"

    def test_dumps_float(self):
        s = create_json_serializer()
        assert s.dumps(3.14) == json.dumps(3.14)

    def test_dumps_unicode(self):
        s = create_json_serializer()
        assert s.dumps("données") == json.dumps("données")

    def test_dumps_returns_str(self):
        s = create_json_serializer()
        assert isinstance(s.dumps({}), str)

    def test_loads_dict(self):
        s = create_json_serializer()
        assert s.loads('{"a": 1}') == {"a": 1}

    def test_loads_list(self):
        s = create_json_serializer()
        assert s.loads("[1, 2, 3]") == [1, 2, 3]

    def test_loads_null(self):
        s = create_json_serializer()
        assert s.loads("null") is None

    def test_loads_bool_true(self):
        s = create_json_serializer()
        assert s.loads("true") is True

    def test_loads_bool_false(self):
        s = create_json_serializer()
        assert s.loads("false") is False

    def test_loads_number(self):
        s = create_json_serializer()
        assert s.loads("42") == 42

    def test_roundtrip(self):
        s = create_json_serializer()
        original = {"symbol": "BTCUSDT", "side": "Buy", "qty": "0.001"}
        assert s.loads(s.dumps(original)) == original

    def test_dumps_error_propagates(self):
        s = create_json_serializer()
        with pytest.raises((TypeError, ValueError)):
            s.dumps(object())

    def test_loads_error_propagates(self):
        s = create_json_serializer()
        with pytest.raises((json.JSONDecodeError, ValueError)):
            s.loads("not valid json {{{")

    def test_matches_stdlib_dumps_exactly(self):
        s = create_json_serializer()
        payload = {"retCode": 0, "retMsg": "OK", "qty": "0.001"}
        assert s.dumps(payload) == json.dumps(payload)


# ---------------------------------------------------------------------------
# 8. Compartición compositiva entre builder y parser
# ---------------------------------------------------------------------------

class TestSharedIdentity:
    def test_shared_serializer_in_builder_and_parser(self):
        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        spy_header = SpyHeaderBuilder()

        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=spy_header,
        )
        parser = create_bybit_response_parser(serializer=serializer)

        assert builder._serializer is serializer
        assert parser._serializer is serializer

    def test_builder_and_parser_share_same_instance(self):
        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        spy_header = SpyHeaderBuilder()

        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=spy_header,
        )
        parser = create_bybit_response_parser(serializer=serializer)

        assert builder._serializer is parser._serializer

    def test_no_extra_serializer_created(self):
        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        spy_header = SpyHeaderBuilder()

        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=spy_header,
        )
        parser = create_bybit_response_parser(serializer=serializer)

        assert type(builder._serializer) is StandardJsonSerializer
        assert type(parser._serializer) is StandardJsonSerializer

    def test_no_serialization_during_composition(self, monkeypatch):
        calls = []
        original_dumps = json.dumps
        monkeypatch.setattr(json, "dumps", lambda *a, **kw: calls.append(a) or original_dumps(*a, **kw))

        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        spy_header = SpyHeaderBuilder()
        create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=spy_header,
        )
        create_bybit_response_parser(serializer=serializer)
        assert calls == []

    def test_builder_accepts_serializer_from_factory(self):
        serializer = create_json_serializer()
        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=SpyAuthenticator(),
            header_builder=SpyHeaderBuilder(),
        )
        assert isinstance(builder, BybitRequestBuilder)

    def test_parser_accepts_serializer_from_factory(self):
        serializer = create_json_serializer()
        parser = create_bybit_response_parser(serializer=serializer)
        assert isinstance(parser, BybitResponseParser)


# ---------------------------------------------------------------------------
# 9. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self):
        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        spy_header = SpyHeaderBuilder()

        transport = create_http_transport()
        executor = create_http_request_executor(transport=transport, timeout_seconds=5.0)
        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=spy_header,
        )
        sender = create_bybit_private_request_sender(
            request_builder=builder,
            request_executor=executor,
        )
        parser = create_bybit_response_parser(serializer=serializer)
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)
        gateway = create_bybit_demo_execution_gateway(private_api=private_api)

        return (
            gateway,
            serializer,
            transport,
            executor,
            builder,
            sender,
            parser,
            private_api,
            spy_auth,
            spy_header,
        )

    def test_full_stack_builds_correctly(self):
        gateway, *_ = self._build_full_stack()
        assert isinstance(gateway, BybitExecutionGateway)

    def test_serializer_shared_in_builder_and_parser(self):
        _, serializer, _, _, builder, _, parser, *_ = self._build_full_stack()
        assert builder._serializer is serializer
        assert parser._serializer is serializer

    def test_transport_identity_in_executor(self):
        _, _, transport, executor, *_ = self._build_full_stack()
        assert executor._transport is transport

    def test_executor_identity_in_sender(self):
        _, _, _, executor, _, sender, *_ = self._build_full_stack()
        assert sender._request_executor is executor

    def test_sender_identity_in_private_api(self):
        _, _, _, _, _, sender, _, private_api, *_ = self._build_full_stack()
        assert private_api._sender is sender

    def test_parser_identity_in_private_api(self):
        _, _, _, _, _, _, parser, private_api, *_ = self._build_full_stack()
        assert private_api._response_parser is parser

    def test_no_dumps_during_full_composition(self, monkeypatch):
        calls = []
        original = json.dumps
        monkeypatch.setattr(json, "dumps", lambda *a, **kw: calls.append(a) or original(*a, **kw))
        self._build_full_stack()
        assert calls == []

    def test_no_auth_during_composition(self):
        *_, spy_auth, spy_header = self._build_full_stack()
        assert spy_auth.calls == []
        assert spy_header.calls == []


# ---------------------------------------------------------------------------
# 10. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_http_transport(self):
        assert "HttpTransport" not in vars(_module)
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_request_builder(self):
        assert "BybitRequestBuilder" not in vars(_module)

    def test_does_not_import_response_parser(self):
        assert "BybitResponseParser" not in vars(_module)

    def test_does_not_contain_bybit_config(self):
        src = inspect.getsource(create_json_serializer)
        assert "bybit" not in src.lower()
        assert "api_key" not in src
        assert "BYBIT_" not in src

    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
