import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_demo_credentials_factory as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.system_millisecond_clock import SystemMillisecondClock


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_credentials_factory import (
            create_bybit_demo_credentials as f,
        )
        assert f is create_bybit_demo_credentials

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_credentials")
        assert execution_gateway.create_bybit_demo_credentials is create_bybit_demo_credentials

    def test_included_in_all(self):
        assert "create_bybit_demo_credentials" in execution_gateway.__all__

    def test_single_factory_for_bybit_demo_credentials(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "credentials" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_demo_credentials"

    def test_callable(self):
        assert callable(create_bybit_demo_credentials)

    def test_return_annotation_is_bybit_demo_credentials(self):
        hints = inspect.get_annotations(create_bybit_demo_credentials, eval_str=True)
        assert hints.get("return") is BybitDemoCredentials


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_all_parameters_keyword_only(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        for param in sig.parameters.values():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY, (
                f"Parameter {param.name!r} is not keyword-only"
            )

    def test_has_api_key_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "api_key" in sig.parameters

    def test_has_api_secret_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "api_secret" in sig.parameters

    def test_exactly_two_parameters(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert len(sig.parameters) == 2

    def test_no_clock_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "clock" not in sig.parameters

    def test_no_signer_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "signer" not in sig.parameters

    def test_no_authenticator_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "authenticator" not in sig.parameters

    def test_no_serializer_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "serializer" not in sig.parameters

    def test_no_transport_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "transport" not in sig.parameters

    def test_no_url_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "url" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "environment" not in sig.parameters

    def test_no_recv_window_parameter(self):
        sig = inspect.signature(create_bybit_demo_credentials)
        assert "recv_window_ms" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(_VALID_KEY, _VALID_SECRET)


# ---------------------------------------------------------------------------
# 3. Validación — API key
# ---------------------------------------------------------------------------

class TestApiKeyValidation:
    def test_valid_key_accepted(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c, BybitDemoCredentials)

    def test_empty_key_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key="", api_secret=_VALID_SECRET)

    def test_whitespace_only_key_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key="   ", api_secret=_VALID_SECRET)

    def test_tab_only_key_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key="\t", api_secret=_VALID_SECRET)

    def test_newline_only_key_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key="\n", api_secret=_VALID_SECRET)

    def test_none_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=None, api_secret=_VALID_SECRET)

    def test_int_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=123, api_secret=_VALID_SECRET)

    def test_bool_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=True, api_secret=_VALID_SECRET)

    def test_bytes_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=b"demo-key", api_secret=_VALID_SECRET)

    def test_list_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=["demo-key"], api_secret=_VALID_SECRET)

    def test_dict_key_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key={"key": "demo-key"}, api_secret=_VALID_SECRET)

    def test_empty_key_error_message(self):
        with pytest.raises(ValueError, match="api_key must not be empty or whitespace-only"):
            create_bybit_demo_credentials(api_key="", api_secret=_VALID_SECRET)

    def test_none_key_error_message(self):
        with pytest.raises(TypeError, match="api_key must be str"):
            create_bybit_demo_credentials(api_key=None, api_secret=_VALID_SECRET)

    def test_key_with_leading_space_accepted(self):
        c = create_bybit_demo_credentials(api_key=" demo-key", api_secret=_VALID_SECRET)
        assert c.api_key == " demo-key"

    def test_key_with_trailing_space_accepted(self):
        c = create_bybit_demo_credentials(api_key="demo-key ", api_secret=_VALID_SECRET)
        assert c.api_key == "demo-key "

    def test_key_with_internal_space_accepted(self):
        c = create_bybit_demo_credentials(api_key="demo key", api_secret=_VALID_SECRET)
        assert c.api_key == "demo key"


# ---------------------------------------------------------------------------
# 4. Validación — API secret
# ---------------------------------------------------------------------------

class TestApiSecretValidation:
    def test_valid_secret_accepted(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c, BybitDemoCredentials)

    def test_empty_secret_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="")

    def test_whitespace_only_secret_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="   ")

    def test_tab_only_secret_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="\t")

    def test_newline_only_secret_raises_value_error(self):
        with pytest.raises(ValueError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="\n")

    def test_none_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=None)

    def test_int_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=456)

    def test_bool_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=False)

    def test_bytes_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=b"demo-secret")

    def test_list_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=["demo-secret"])

    def test_dict_secret_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret={"s": "v"})

    def test_empty_secret_error_message(self):
        with pytest.raises(ValueError, match="api_secret must not be empty or whitespace-only"):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="")

    def test_none_secret_error_message(self):
        with pytest.raises(TypeError, match="api_secret must be str"):
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=None)

    def test_secret_with_leading_space_accepted(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=" demo-secret")
        assert c.api_secret == " demo-secret"

    def test_secret_with_trailing_space_accepted(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="demo-secret ")
        assert c.api_secret == "demo-secret "

    def test_secret_with_internal_space_accepted(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret="demo secret")
        assert c.api_secret == "demo secret"


# ---------------------------------------------------------------------------
# 5. Ausencia de conversión
# ---------------------------------------------------------------------------

class TestNoConversion:
    def test_api_key_preserved_exactly(self):
        key = "MyExactKey-123"
        c = create_bybit_demo_credentials(api_key=key, api_secret=_VALID_SECRET)
        assert c.api_key == key

    def test_api_secret_preserved_exactly(self):
        secret = "MyExactSecret-456"
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=secret)
        assert c.api_secret == secret

    def test_key_not_stripped(self):
        key = " padded-key "
        c = create_bybit_demo_credentials(api_key=key, api_secret=_VALID_SECRET)
        assert c.api_key == key

    def test_secret_not_stripped(self):
        secret = " padded-secret "
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=secret)
        assert c.api_secret == secret

    def test_key_case_preserved(self):
        key = "MixedCaseKey"
        c = create_bybit_demo_credentials(api_key=key, api_secret=_VALID_SECRET)
        assert c.api_key == key

    def test_secret_case_preserved(self):
        secret = "MixedCaseSecret"
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=secret)
        assert c.api_secret == secret

    def test_key_not_encoded_to_bytes(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c.api_key, str)

    def test_secret_not_encoded_to_bytes(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c.api_secret, str)


# ---------------------------------------------------------------------------
# 6. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_demo_credentials(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c, BybitDemoCredentials)

    def test_returns_exact_type(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert type(c) is BybitDemoCredentials

    def test_does_not_return_tuple(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert not isinstance(c, tuple)

    def test_does_not_return_dict(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert not isinstance(c, dict)

    def test_does_not_return_none(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c is not None

    def test_does_not_return_callable(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert not callable(c)

    def test_api_key_attribute(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c.api_key == _VALID_KEY

    def test_api_secret_attribute(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c.api_secret == _VALID_SECRET

    def test_repr_hides_secret(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        r = repr(c)
        assert _VALID_SECRET not in r

    def test_repr_shows_api_key(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        r = repr(c)
        assert _VALID_KEY in r


# ---------------------------------------------------------------------------
# 7. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_new_instance_per_call(self):
        c1 = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        c2 = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c1 is not c2

    def test_multiple_instances_all_distinct(self):
        instances = [
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
            for _ in range(4)
        ]
        ids = [id(c) for c in instances]
        assert len(set(ids)) == 4

    def test_no_singleton(self):
        c1 = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        c2 = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c1 is not c2

    def test_each_is_bybit_demo_credentials(self):
        for _ in range(3):
            c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
            assert type(c) is BybitDemoCredentials


# ---------------------------------------------------------------------------
# 8. Seguridad estática
# ---------------------------------------------------------------------------

class TestStaticSecurity:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_import_dotenv(self):
        assert "dotenv" not in vars(_module)
        assert "load_dotenv" not in vars(_module)

    def test_does_not_import_pathlib(self):
        assert "pathlib" not in vars(_module)
        assert "Path" not in vars(_module)

    def test_does_not_import_logging(self):
        assert "logging" not in vars(_module)

    def test_does_not_import_print(self):
        src = inspect.getsource(_module)
        assert "print(" not in src

    def test_source_does_not_contain_env_var_names(self):
        src = inspect.getsource(_module)
        assert "BYBIT_API_KEY" not in src
        assert "BYBIT_API_SECRET" not in src

    def test_source_does_not_contain_base_url(self):
        src = inspect.getsource(_module)
        assert "bybit.com" not in src

    def test_source_does_not_use_open(self):
        src = inspect.getsource(_module)
        assert "open(" not in src

    def test_source_does_not_contain_literal_secrets(self):
        src = inspect.getsource(_module)
        assert "AAAA" not in src
        assert "secret_value" not in src

    def test_does_not_contain_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)
        assert "create_bybit_authenticator" not in vars(_module)

    def test_does_not_contain_signer(self):
        assert "MessageSigner" not in vars(_module)
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_contain_serializer(self):
        assert "JsonSerializer" not in vars(_module)
        assert "StandardJsonSerializer" not in vars(_module)

    def test_does_not_contain_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)

    def test_does_not_contain_transport(self):
        assert "HttpTransport" not in vars(_module)
        assert "UrllibHttpTransport" not in vars(_module)


# ---------------------------------------------------------------------------
# 9. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_network_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "should-not-be-used")
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c.api_key == _VALID_KEY

    def test_env_key_not_used(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "env-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "env-secret")
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert c.api_key == _VALID_KEY
        assert c.api_secret == _VALID_SECRET


# ---------------------------------------------------------------------------
# 10. Comportamiento integrado mínimo
# ---------------------------------------------------------------------------

class TestIntegratedMinimumBehavior:
    def test_credentials_satisfy_standard_bybit_authenticator_type(self):
        c = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        assert isinstance(c, BybitDemoCredentials)

    def test_credentials_accepted_by_create_bybit_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=5_000,
        )
        assert isinstance(auth, StandardBybitAuthenticator)

    def test_credentials_identity_preserved_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=5_000,
        )
        assert auth._credentials is credentials

    def test_no_clock_call_during_composition(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=5_000,
        )
        assert calls == []

    def test_no_signer_call_during_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append((secret, message))
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=5_000,
        )
        assert calls == []


# ---------------------------------------------------------------------------
# 11. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        clock = SystemMillisecondClock()
        signer = HmacSha256Signer()

        authenticator = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        serializer = create_json_serializer()
        header_builder = create_bybit_header_builder()
        transport = create_http_transport()
        executor = create_http_request_executor(transport=transport, timeout_seconds=5.0)

        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=authenticator,
            header_builder=header_builder,
        )
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=executor,
        )
        parser = create_bybit_response_parser(serializer=serializer)
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)
        gateway = create_bybit_demo_execution_gateway(private_api=private_api)

        return dict(
            credentials=credentials,
            authenticator=authenticator,
            serializer=serializer,
            header_builder=header_builder,
            transport=transport,
            executor=executor,
            request_builder=request_builder,
            sender=sender,
            parser=parser,
            private_api=private_api,
            gateway=gateway,
        )

    def test_full_stack_builds_successfully(self):
        stack = self._build_full_stack()
        assert isinstance(stack["gateway"], BybitExecutionGateway)

    def test_credentials_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._credentials is stack["credentials"]

    def test_authenticator_identity_in_request_builder(self):
        stack = self._build_full_stack()
        assert stack["request_builder"]._authenticator is stack["authenticator"]

    def test_serializer_shared_in_builder_and_parser(self):
        stack = self._build_full_stack()
        assert stack["request_builder"]._serializer is stack["serializer"]
        assert stack["parser"]._serializer is stack["serializer"]

    def test_header_builder_identity_in_request_builder(self):
        stack = self._build_full_stack()
        assert stack["request_builder"]._header_builder is stack["header_builder"]

    def test_transport_identity_in_executor(self):
        stack = self._build_full_stack()
        assert stack["executor"]._transport is stack["transport"]

    def test_executor_identity_in_sender(self):
        stack = self._build_full_stack()
        assert stack["sender"]._request_executor is stack["executor"]

    def test_no_network_during_full_composition(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            self._build_full_stack()
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_clock_called_during_full_composition(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        self._build_full_stack()
        assert calls == []

    def test_no_signing_during_full_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        self._build_full_stack()
        assert calls == []


# ---------------------------------------------------------------------------
# 12. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_factory_source_is_minimal(self):
        src = inspect.getsource(create_bybit_demo_credentials)
        assert "os.environ" not in src
        assert "os.getenv" not in src
        assert "open(" not in src
        assert "print(" not in src
        assert ".env" not in src
        assert "logging" not in src
