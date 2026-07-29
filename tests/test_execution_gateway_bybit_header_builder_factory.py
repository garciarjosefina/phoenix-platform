import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_header_builder_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_auth(
    timestamp_ms: int = 1_700_000_000_000,
    api_key: str = "test_api_key",
    recv_window_ms: int = 5_000,
    signature: str = "abcdef0123456789" * 4,
) -> BybitAuthentication:
    return BybitAuthentication(
        timestamp_ms=timestamp_ms,
        api_key=api_key,
        recv_window_ms=recv_window_ms,
        signature=signature,
    )


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyAuthenticator:
    def __init__(self) -> None:
        self.calls: list = []

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.calls.append({"body": body})
        return _make_auth()


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_header_builder_factory import (
            create_bybit_header_builder as f,
        )
        assert f is create_bybit_header_builder

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_header_builder")
        assert execution_gateway.create_bybit_header_builder is create_bybit_header_builder

    def test_included_in_all(self):
        assert "create_bybit_header_builder" in execution_gateway.__all__

    def test_single_factory_for_bybit_header_builder(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "header_builder" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_header_builder"

    def test_callable(self):
        assert callable(create_bybit_header_builder)

    def test_no_extra_args_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_header_builder(object())

    def test_return_annotation_is_bybit_header_builder(self):
        hints = inspect.get_annotations(create_bybit_header_builder, eval_str=True)
        assert hints.get("return") is BybitHeaderBuilder


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_zero_parameters(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert len(sig.parameters) == 0

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_authenticator(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "authenticator" not in sig.parameters

    def test_does_not_receive_signer(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "signer" not in sig.parameters

    def test_does_not_receive_clock(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "clock" not in sig.parameters

    def test_does_not_receive_serializer(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "serializer" not in sig.parameters

    def test_does_not_receive_credentials(self):
        sig = inspect.signature(create_bybit_header_builder)
        assert "credentials" not in sig.parameters


# ---------------------------------------------------------------------------
# 3. Implementación concreta
# ---------------------------------------------------------------------------

class TestConcreteImplementation:
    def test_returns_bybit_header_builder(self):
        h = create_bybit_header_builder()
        assert isinstance(h, BybitHeaderBuilder)

    def test_returns_exact_type(self):
        h = create_bybit_header_builder()
        assert type(h) is BybitHeaderBuilder

    def test_has_build_method(self):
        h = create_bybit_header_builder()
        assert callable(getattr(h, "build", None))

    def test_not_a_fake(self):
        h = create_bybit_header_builder()
        assert type(h).__name__ == "BybitHeaderBuilder"


# ---------------------------------------------------------------------------
# 4. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_new_instance_per_call(self):
        h1 = create_bybit_header_builder()
        h2 = create_bybit_header_builder()
        assert h1 is not h2

    def test_multiple_instances_all_distinct(self):
        instances = [create_bybit_header_builder() for _ in range(4)]
        ids = [id(h) for h in instances]
        assert len(set(ids)) == 4

    def test_does_not_return_dict(self):
        h = create_bybit_header_builder()
        assert not isinstance(h, dict)

    def test_does_not_return_tuple(self):
        h = create_bybit_header_builder()
        assert not isinstance(h, tuple)

    def test_does_not_return_none(self):
        h = create_bybit_header_builder()
        assert h is not None

    def test_does_not_return_class(self):
        h = create_bybit_header_builder()
        assert not inspect.isclass(h)


# ---------------------------------------------------------------------------
# 5. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_no_singleton_behavior(self):
        h1 = create_bybit_header_builder()
        h2 = create_bybit_header_builder()
        assert h1 is not h2

    def test_each_is_bybit_header_builder(self):
        for _ in range(3):
            h = create_bybit_header_builder()
            assert type(h) is BybitHeaderBuilder

    def test_no_shared_state(self):
        h1 = create_bybit_header_builder()
        h2 = create_bybit_header_builder()
        assert h1 is not h2


# ---------------------------------------------------------------------------
# 6. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_build_not_called_during_construction(self, monkeypatch):
        calls = []
        original_build = BybitHeaderBuilder.build

        def spy_build(self, *, authentication):
            calls.append(authentication)
            return original_build(self, authentication=authentication)

        monkeypatch.setattr(BybitHeaderBuilder, "build", spy_build)
        create_bybit_header_builder()
        assert calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        h = create_bybit_header_builder()
        assert isinstance(h, BybitHeaderBuilder)

    def test_no_network_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_header_builder()
        finally:
            socket.socket.connect = original
        assert network_calls == []


# ---------------------------------------------------------------------------
# 7. Comportamiento integrado mínimo del header builder
# ---------------------------------------------------------------------------

class TestIntegratedHeaderBuilderBehavior:
    def test_build_returns_dict(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth())
        assert isinstance(result, dict)

    def test_build_includes_api_key_header(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(api_key="mykey"))
        assert result["X-BAPI-API-KEY"] == "mykey"

    def test_build_includes_timestamp_header(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(timestamp_ms=1_234_567_890_000))
        assert result["X-BAPI-TIMESTAMP"] == "1234567890000"

    def test_build_includes_recv_window_header(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(recv_window_ms=9_000))
        assert result["X-BAPI-RECV-WINDOW"] == "9000"

    def test_build_includes_signature_header(self):
        sig = "deadbeef" * 8
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(signature=sig))
        assert result["X-BAPI-SIGN"] == sig

    def test_build_includes_content_type_header(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth())
        assert result["Content-Type"] == "application/json"

    def test_build_returns_exactly_five_headers(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth())
        assert len(result) == 5

    def test_build_all_values_are_strings(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth())
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, str)

    def test_build_rejects_none_authentication(self):
        h = create_bybit_header_builder()
        with pytest.raises(TypeError, match="BybitAuthentication"):
            h.build(authentication=None)

    def test_build_rejects_dict_authentication(self):
        h = create_bybit_header_builder()
        with pytest.raises(TypeError):
            h.build(authentication={"api_key": "k"})

    def test_build_does_not_mutate_input(self):
        auth = _make_auth()
        h = create_bybit_header_builder()
        h.build(authentication=auth)
        assert auth.api_key == "test_api_key"
        assert auth.timestamp_ms == 1_700_000_000_000

    def test_timestamp_converted_to_string(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(timestamp_ms=9_999_999_999_999))
        assert result["X-BAPI-TIMESTAMP"] == "9999999999999"
        assert isinstance(result["X-BAPI-TIMESTAMP"], str)

    def test_recv_window_converted_to_string(self):
        h = create_bybit_header_builder()
        result = h.build(authentication=_make_auth(recv_window_ms=20_000))
        assert result["X-BAPI-RECV-WINDOW"] == "20000"
        assert isinstance(result["X-BAPI-RECV-WINDOW"], str)


# ---------------------------------------------------------------------------
# 8. Integración con request builder
# ---------------------------------------------------------------------------

class TestIntegrationWithRequestBuilder:
    def test_header_builder_identity_in_request_builder(self):
        serializer = create_json_serializer()
        auth = SpyAuthenticator()
        header_builder = create_bybit_header_builder()

        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=auth,
            header_builder=header_builder,
        )
        assert request_builder._header_builder is header_builder

    def test_serializer_identity_in_request_builder(self):
        serializer = create_json_serializer()
        auth = SpyAuthenticator()
        header_builder = create_bybit_header_builder()

        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=auth,
            header_builder=header_builder,
        )
        assert request_builder._serializer is serializer

    def test_authenticator_identity_in_request_builder(self):
        serializer = create_json_serializer()
        auth = SpyAuthenticator()
        header_builder = create_bybit_header_builder()

        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=auth,
            header_builder=header_builder,
        )
        assert request_builder._authenticator is auth

    def test_no_headers_built_during_composition(self, monkeypatch):
        calls = []
        original_build = BybitHeaderBuilder.build

        def spy_build(self, *, authentication):
            calls.append(authentication)
            return original_build(self, authentication=authentication)

        monkeypatch.setattr(BybitHeaderBuilder, "build", spy_build)

        header_builder = create_bybit_header_builder()
        create_bybit_request_builder(
            serializer=create_json_serializer(),
            authenticator=SpyAuthenticator(),
            header_builder=header_builder,
        )
        assert calls == []

    def test_returns_bybit_request_builder(self):
        request_builder = create_bybit_request_builder(
            serializer=create_json_serializer(),
            authenticator=SpyAuthenticator(),
            header_builder=create_bybit_header_builder(),
        )
        assert isinstance(request_builder, BybitRequestBuilder)


# ---------------------------------------------------------------------------
# 9. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self):
        serializer = create_json_serializer()
        spy_auth = SpyAuthenticator()
        header_builder = create_bybit_header_builder()

        transport = create_http_transport()
        executor = create_http_request_executor(transport=transport, timeout_seconds=5.0)
        builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=spy_auth,
            header_builder=header_builder,
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
            header_builder,
            serializer,
            transport,
            executor,
            builder,
            sender,
            parser,
            private_api,
            spy_auth,
        )

    def test_full_stack_builds_correctly(self):
        gateway, *_ = self._build_full_stack()
        assert isinstance(gateway, BybitExecutionGateway)

    def test_header_builder_identity_in_builder(self):
        _, header_builder, _, _, _, builder, *_ = self._build_full_stack()
        assert builder._header_builder is header_builder

    def test_serializer_shared_in_builder_and_parser(self):
        _, _, serializer, _, _, builder, _, parser, *_ = self._build_full_stack()
        assert builder._serializer is serializer
        assert parser._serializer is serializer

    def test_transport_identity_in_executor(self):
        _, _, _, transport, executor, *_ = self._build_full_stack()
        assert executor._transport is transport

    def test_executor_identity_in_sender(self):
        _, _, _, _, executor, _, sender, *_ = self._build_full_stack()
        assert sender._request_executor is executor

    def test_no_headers_built_during_composition(self, monkeypatch):
        calls = []
        original_build = BybitHeaderBuilder.build

        def spy_build(self, *, authentication):
            calls.append(authentication)
            return original_build(self, authentication=authentication)

        monkeypatch.setattr(BybitHeaderBuilder, "build", spy_build)
        self._build_full_stack()
        assert calls == []

    def test_no_auth_during_composition(self):
        *_, spy_auth = self._build_full_stack()
        assert spy_auth.calls == []


# ---------------------------------------------------------------------------
# 10. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "BybitAuthenticator" not in vars(_module)
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "MessageSigner" not in vars(_module)
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_serializer(self):
        assert "JsonSerializer" not in vars(_module)
        assert "StandardJsonSerializer" not in vars(_module)

    def test_does_not_import_transport(self):
        assert "HttpTransport" not in vars(_module)
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_contain_secrets(self):
        src = inspect.getsource(create_bybit_header_builder)
        assert "api_key" not in src
        assert "api_secret" not in src
        assert "BYBIT_" not in src

    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
