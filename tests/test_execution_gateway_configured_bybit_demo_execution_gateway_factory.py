import inspect

import pytest

import execution_gateway
import execution_gateway.configured_bybit_demo_execution_gateway_factory as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.configured_bybit_demo_execution_gateway_factory import (
    create_configured_bybit_demo_execution_gateway,
)
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.standard_json_serializer import StandardJsonSerializer
from execution_gateway.system_millisecond_clock import SystemMillisecondClock
from execution_gateway.urllib_http_transport import UrllibHttpTransport


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"
_VALID_RECV_WINDOW_MS = 5_000
_VALID_TIMEOUT_SECONDS = 5.0

# Nombre de cada factory inferior, tal como fue importada dentro del módulo
# `configured_bybit_demo_execution_gateway_factory`, mapeado a la clave bajo
# la cual se captura su valor de retorno real en `_build_with_capture`.
_CAPTURE_MAP = {
    "create_bybit_demo_credentials": "credentials",
    "create_message_signer": "signer",
    "create_millisecond_clock": "clock",
    "create_bybit_recv_window_ms": "recv_window_ms",
    "create_bybit_authenticator": "authenticator",
    "create_json_serializer": "serializer",
    "create_bybit_header_builder": "header_builder",
    "create_bybit_request_builder": "request_builder",
    "create_bybit_response_parser": "response_parser",
    "create_http_transport": "transport",
    "create_http_timeout_seconds": "timeout_seconds",
    "create_http_request_executor": "request_executor",
    "create_bybit_private_request_sender": "sender",
    "create_bybit_private_api": "private_api",
    "create_bybit_demo_execution_gateway": "gateway",
}


def _build(**overrides):
    kwargs = dict(
        api_key=_VALID_KEY,
        api_secret=_VALID_SECRET,
        recv_window_ms=_VALID_RECV_WINDOW_MS,
        timeout_seconds=_VALID_TIMEOUT_SECONDS,
    )
    kwargs.update(overrides)
    return create_configured_bybit_demo_execution_gateway(**kwargs)


def _build_with_capture(monkeypatch, **overrides):
    """Ejecuta la factory real, espiando cada factory inferior importada en
    el módulo para capturar el objeto que ella misma retornó. Cada spy
    delega en la función original y devuelve exactamente lo que ésta
    produjo — no sustituye ni fabrica objetos falsos."""
    captured: dict[str, object] = {}
    for factory_name, key in _CAPTURE_MAP.items():
        original = getattr(_module, factory_name)

        def spy(*args, __original=original, __key=key, **kwargs):
            result = __original(*args, **kwargs)
            captured[__key] = result
            return result

        monkeypatch.setattr(_module, factory_name, spy)

    gateway = _build(**overrides)
    return gateway, captured


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.configured_bybit_demo_execution_gateway_factory import (
            create_configured_bybit_demo_execution_gateway as f,
        )
        assert f is create_configured_bybit_demo_execution_gateway

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_configured_bybit_demo_execution_gateway")
        assert (
            execution_gateway.create_configured_bybit_demo_execution_gateway
            is create_configured_bybit_demo_execution_gateway
        )

    def test_included_in_all(self):
        assert "create_configured_bybit_demo_execution_gateway" in execution_gateway.__all__

    def test_callable(self):
        assert callable(create_configured_bybit_demo_execution_gateway)

    def test_single_top_level_factory_in_module(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and getattr(_module, name).__module__ == _module.__name__
        ]
        assert factory_names == ["create_configured_bybit_demo_execution_gateway"]


# ---------------------------------------------------------------------------
# 2. Firma
# ---------------------------------------------------------------------------

class TestSignature:
    def test_all_parameters_keyword_only(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        for param in sig.parameters.values():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_names(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        assert set(sig.parameters) == {
            "api_key",
            "api_secret",
            "recv_window_ms",
            "timeout_seconds",
        }

    def test_no_base_url_parameter(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        assert "base_url" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        assert "environment" not in sig.parameters

    def test_no_credentials_object_parameter(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        assert "credentials" not in sig.parameters

    def test_no_default_values(self):
        sig = inspect.signature(create_configured_bybit_demo_execution_gateway)
        for param in sig.parameters.values():
            assert param.default is inspect.Parameter.empty

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_configured_bybit_demo_execution_gateway(
                _VALID_KEY, _VALID_SECRET, _VALID_RECV_WINDOW_MS, _VALID_TIMEOUT_SECONDS
            )

    def test_return_annotation_is_bybit_execution_gateway(self):
        hints = inspect.get_annotations(
            create_configured_bybit_demo_execution_gateway, eval_str=True
        )
        assert hints.get("return") is BybitExecutionGateway


# ---------------------------------------------------------------------------
# 3. Composición completa
# ---------------------------------------------------------------------------

class TestFullComposition:
    def test_returns_bybit_execution_gateway(self):
        gateway = _build()
        assert isinstance(gateway, BybitExecutionGateway)

    def test_client_present(self):
        gateway = _build()
        assert gateway._client is not None

    def test_authenticator_type(self):
        gateway = _build()
        authenticator = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        assert isinstance(authenticator, StandardBybitAuthenticator)

    def test_credentials_type(self):
        gateway = _build()
        credentials = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        assert isinstance(credentials, BybitDemoCredentials)

    def test_credentials_values(self):
        gateway = _build(api_key="my-key", api_secret="my-secret")
        credentials = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        assert credentials.api_key == "my-key"
        assert credentials.api_secret == "my-secret"

    def test_signer_type(self):
        gateway = _build()
        signer = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._signer
        assert isinstance(signer, HmacSha256Signer)

    def test_clock_type(self):
        gateway = _build()
        clock = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._clock
        assert isinstance(clock, SystemMillisecondClock)

    def test_recv_window_ms_value(self):
        gateway = _build(recv_window_ms=7_500)
        authenticator = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        assert authenticator._recv_window_ms == 7_500

    def test_transport_type(self):
        gateway = _build()
        transport = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport
        assert isinstance(transport, UrllibHttpTransport)

    def test_request_executor_type(self):
        gateway = _build()
        executor = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor
        assert isinstance(executor, HttpRequestExecutor)

    def test_timeout_seconds_value(self):
        gateway = _build(timeout_seconds=12.5)
        executor = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor
        assert executor._timeout_seconds == 12.5

    def test_serializer_shared_between_builder_and_parser(self):
        gateway = _build()
        chain = gateway._client._create_order_operation._endpoint_executor._private_api
        assert chain._sender._request_builder._serializer is chain._response_parser._serializer

    def test_base_url_matches_demo_constant(self):
        from execution_gateway.bybit_demo_execution_gateway_factory import _BYBIT_DEMO_BASE_URL
        gateway = _build()
        url_builder = gateway._client._create_order_operation._endpoint_executor._url_builder
        assert url_builder._base_url == _BYBIT_DEMO_BASE_URL


# ---------------------------------------------------------------------------
# 4. Propagación exacta de excepciones
# ---------------------------------------------------------------------------

class TestExceptionPropagation:
    def test_invalid_api_key_type_raises_type_error(self):
        with pytest.raises(TypeError, match="api_key must be str"):
            _build(api_key=123)

    def test_empty_api_key_raises_value_error(self):
        with pytest.raises(ValueError, match="api_key must not be empty or whitespace-only"):
            _build(api_key="")

    def test_empty_api_secret_raises_value_error(self):
        with pytest.raises(ValueError, match="api_secret must not be empty or whitespace-only"):
            _build(api_secret="   ")

    def test_invalid_recv_window_type_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int"):
            _build(recv_window_ms="5000")

    def test_bool_recv_window_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: bool"):
            _build(recv_window_ms=True)

    def test_negative_recv_window_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            _build(recv_window_ms=-1)

    def test_zero_recv_window_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            _build(recv_window_ms=0)

    def test_invalid_timeout_type_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float"):
            _build(timeout_seconds="5")

    def test_bool_timeout_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: bool"):
            _build(timeout_seconds=True)

    def test_negative_timeout_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _build(timeout_seconds=-5.0)

    def test_zero_timeout_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            _build(timeout_seconds=0)

    def test_error_messages_match_lower_factories_exactly(self):
        try:
            _build(recv_window_ms=0)
            assert False, "expected ValueError"
        except ValueError as e:
            direct_error = None
            try:
                create_bybit_recv_window_ms(recv_window_ms=0)
            except ValueError as direct:
                direct_error = str(direct)
            assert str(e) == direct_error

    def test_timeout_error_messages_match_lower_factory_exactly(self):
        try:
            _build(timeout_seconds=0)
            assert False, "expected ValueError"
        except ValueError as e:
            direct_error = None
            try:
                create_http_timeout_seconds(timeout_seconds=0)
            except ValueError as direct:
                direct_error = str(direct)
            assert str(e) == direct_error


# ---------------------------------------------------------------------------
# 5. Identidad de dependencias
#
# Cada test espía la factory inferior correspondiente (ver _build_with_capture),
# captura el objeto real que ésta retornó, y navega el grafo efectivamente
# construido para comprobar por `is` que ese mismo objeto -y no una copia ni
# una instancia nueva equivalente- es el que quedó inyectado.
# ---------------------------------------------------------------------------

class TestIdentity:
    def test_credentials_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        graph_credentials = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        assert graph_credentials is captured["credentials"]

    def test_signer_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        graph_signer = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._signer
        assert graph_signer is captured["signer"]

    def test_clock_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        graph_clock = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._clock
        assert graph_clock is captured["clock"]

    def test_recv_window_ms_value_and_type(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        authenticator = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        assert authenticator._recv_window_ms == captured["recv_window_ms"]
        assert type(authenticator._recv_window_ms) is type(captured["recv_window_ms"])

    def test_authenticator_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        graph_authenticator = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator
        assert graph_authenticator is captured["authenticator"]

    def test_serializer_identity_shared_between_builder_and_parser(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        chain = gateway._client._create_order_operation._endpoint_executor._private_api
        request_builder_serializer = chain._sender._request_builder._serializer
        response_parser_serializer = chain._response_parser._serializer
        assert request_builder_serializer is captured["serializer"]
        assert response_parser_serializer is captured["serializer"]
        assert request_builder_serializer is response_parser_serializer

    def test_header_builder_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        request_builder = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder
        assert request_builder._header_builder is captured["header_builder"]

    def test_request_builder_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        sender = gateway._client._create_order_operation._endpoint_executor._private_api._sender
        assert sender._request_builder is captured["request_builder"]

    def test_response_parser_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        private_api = gateway._client._create_order_operation._endpoint_executor._private_api
        assert private_api._response_parser is captured["response_parser"]

    def test_transport_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        request_executor = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor
        assert request_executor._transport is captured["transport"]

    def test_timeout_seconds_value_and_type(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        request_executor = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor
        assert request_executor._timeout_seconds == captured["timeout_seconds"]
        assert type(request_executor._timeout_seconds) is type(captured["timeout_seconds"])

    def test_request_executor_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        sender = gateway._client._create_order_operation._endpoint_executor._private_api._sender
        assert sender._request_executor is captured["request_executor"]

    def test_sender_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        private_api = gateway._client._create_order_operation._endpoint_executor._private_api
        assert private_api._sender is captured["sender"]

    def test_private_api_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        endpoint_executor = gateway._client._create_order_operation._endpoint_executor
        assert endpoint_executor._private_api is captured["private_api"]

    def test_gateway_identity(self, monkeypatch):
        gateway, captured = _build_with_capture(monkeypatch)
        assert gateway is captured["gateway"]


# ---------------------------------------------------------------------------
# 5b. Sensibilidad a composición rota (mutación)
#
# Estos tests no rompen producción: sustituyen temporalmente, sólo dentro del
# test, el valor que retorna una factory inferior, y comprueban que ese
# cambio se refleja en el grafo real. Si la factory integral construyera sus
# propias instancias en lugar de reutilizar las inyectadas, o si dejara de
# compartir el serializer, estos tests dejarían de pasar.
# ---------------------------------------------------------------------------

class TestIdentityMutationSensitivity:
    def test_composition_reflects_substituted_signer(self, monkeypatch):
        substituted_signer = HmacSha256Signer()
        monkeypatch.setattr(_module, "create_message_signer", lambda: substituted_signer)
        gateway = _build()
        graph_signer = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._signer
        assert graph_signer is substituted_signer

    def test_composition_reflects_substituted_transport(self, monkeypatch):
        substituted_transport = UrllibHttpTransport()
        monkeypatch.setattr(_module, "create_http_transport", lambda: substituted_transport)
        gateway = _build()
        graph_transport = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport
        assert graph_transport is substituted_transport

    def test_serializer_factory_invoked_exactly_once(self, monkeypatch):
        call_count = 0
        original = _module.create_json_serializer

        def counting_spy():
            nonlocal call_count
            call_count += 1
            return original()

        monkeypatch.setattr(_module, "create_json_serializer", counting_spy)
        _build()
        assert call_count == 1


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas — sin estado compartido
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_different_gateway_instances(self):
        g1 = _build()
        g2 = _build()
        assert g1 is not g2

    def test_two_calls_produce_different_client_instances(self):
        g1 = _build()
        g2 = _build()
        assert g1._client is not g2._client

    def test_two_calls_produce_different_credentials_instances(self):
        g1 = _build()
        g2 = _build()
        c1 = g1._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        c2 = g2._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        assert c1 is not c2

    def test_two_calls_produce_different_signer_instances(self):
        g1 = _build()
        g2 = _build()
        s1 = g1._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._signer
        s2 = g2._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._signer
        assert s1 is not s2

    def test_two_calls_produce_different_transport_instances(self):
        g1 = _build()
        g2 = _build()
        t1 = g1._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport
        t2 = g2._client._create_order_operation._endpoint_executor._private_api._sender._request_executor._transport
        assert t1 is not t2

    def test_no_state_accumulation_across_many_calls(self):
        gateways = [_build() for _ in range(5)]
        clients = {id(g._client) for g in gateways}
        assert len(clients) == 5


# ---------------------------------------------------------------------------
# 7. Ausencia de ejecución durante la composición
# ---------------------------------------------------------------------------

class TestNoExecutionDuringComposition:
    def test_no_network_during_construction(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            _build()
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_dns_resolution_during_construction(self, monkeypatch):
        import socket
        calls = []
        original = socket.getaddrinfo

        def patched(*args, **kwargs):
            calls.append(args)
            return original(*args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", patched)
        _build()
        assert calls == []

    def test_no_http_post_during_construction(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        _build()
        assert calls == []

    def test_no_clock_read_during_construction(self, monkeypatch):
        import time
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        _build()
        assert calls == []

    def test_no_signing_during_construction(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        _build()
        assert calls == []

    def test_no_authentication_call_during_construction(self, monkeypatch):
        calls = []
        original_authenticate = StandardBybitAuthenticator.authenticate

        def spy_authenticate(self, *, body):
            calls.append(True)
            return original_authenticate(self, body=body)

        monkeypatch.setattr(StandardBybitAuthenticator, "authenticate", spy_authenticate)
        _build()
        assert calls == []

    def test_no_serialization_during_construction(self, monkeypatch):
        def explode(self, value):
            raise AssertionError("dumps must not be called during composition")

        monkeypatch.setattr(StandardJsonSerializer, "dumps", explode)
        _build()

    def test_no_deserialization_during_construction(self, monkeypatch):
        def explode(self, value):
            raise AssertionError("loads must not be called during composition")

        monkeypatch.setattr(StandardJsonSerializer, "loads", explode)
        _build()

    def test_no_header_building_during_construction(self, monkeypatch):
        def explode(self, *, authentication):
            raise AssertionError("header builder must not be called during composition")

        monkeypatch.setattr(BybitHeaderBuilder, "build", explode)
        _build()

    def test_no_env_vars_read(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "env-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "env-secret")
        monkeypatch.setenv("BYBIT_BASE_URL", "https://other.example.com")
        gateway = _build()
        credentials = gateway._client._create_order_operation._endpoint_executor._private_api._sender._request_builder._authenticator._credentials
        assert credentials.api_key == _VALID_KEY
        assert credentials.api_secret == _VALID_SECRET

    def test_no_file_reads(self, monkeypatch):
        calls = []
        original_open = open

        def spy_open(*args, **kwargs):
            calls.append(args)
            return original_open(*args, **kwargs)

        import builtins
        monkeypatch.setattr(builtins, "open", spy_open)
        _build()
        assert calls == []


# ---------------------------------------------------------------------------
# 8. Seguridad estática
# ---------------------------------------------------------------------------

class TestStaticSecurity:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_dotenv(self):
        assert "dotenv" not in vars(_module)

    def test_does_not_import_logging(self):
        assert "logging" not in vars(_module)

    def test_source_does_not_use_print(self):
        src = inspect.getsource(_module)
        assert "print(" not in src

    def test_source_does_not_use_open(self):
        src = inspect.getsource(_module)
        assert "open(" not in src

    def test_source_does_not_reference_env_var_names(self):
        src = inspect.getsource(_module)
        assert "BYBIT_API_KEY" not in src
        assert "os.environ" not in src
        assert "os.getenv" not in src

    def test_does_not_hardcode_base_url(self):
        src = inspect.getsource(create_configured_bybit_demo_execution_gateway)
        assert "https://" not in src

    def test_does_not_instantiate_concrete_classes_directly(self):
        src = inspect.getsource(create_configured_bybit_demo_execution_gateway)
        forbidden = [
            "BybitDemoCredentials(",
            "StandardBybitAuthenticator(",
            "HttpRequestExecutor(",
            "BybitPrivateApi(",
            "BybitPrivateRequestSender(",
            "BybitRequestBuilder(",
            "BybitResponseParser(",
            "BybitUrlBuilder(",
            "BybitEndpointExecutor(",
            "HmacSha256Signer(",
            "SystemMillisecondClock(",
            "UrllibHttpTransport(",
            "StandardJsonSerializer(",
            "BybitHeaderBuilder(",
            "BybitExecutionGateway(",
        ]
        for forbidden_call in forbidden:
            assert forbidden_call not in src, f"found direct instantiation: {forbidden_call}"

    def test_only_uses_factory_functions(self):
        src = inspect.getsource(create_configured_bybit_demo_execution_gateway)
        required_calls = [
            "create_bybit_demo_credentials(",
            "create_message_signer(",
            "create_millisecond_clock(",
            "create_bybit_recv_window_ms(",
            "create_bybit_authenticator(",
            "create_json_serializer(",
            "create_bybit_header_builder(",
            "create_bybit_request_builder(",
            "create_bybit_response_parser(",
            "create_http_transport(",
            "create_http_timeout_seconds(",
            "create_http_request_executor(",
            "create_bybit_private_request_sender(",
            "create_bybit_private_api(",
            "create_bybit_demo_execution_gateway(",
        ]
        for required_call in required_calls:
            assert required_call in src, f"missing composition root call: {required_call}"


# ---------------------------------------------------------------------------
# 9. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
