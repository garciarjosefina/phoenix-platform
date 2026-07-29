import hashlib
import hmac as _hmac
import inspect

import pytest

import execution_gateway
import execution_gateway.message_signer_factory as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer import MessageSigner
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.system_millisecond_clock import SystemMillisecondClock


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"


def _expected_hmac(secret: str, message: str) -> str:
    return _hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.message_signer_factory import create_message_signer as f
        assert f is create_message_signer

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_message_signer")
        assert execution_gateway.create_message_signer is create_message_signer

    def test_included_in_all(self):
        assert "create_message_signer" in execution_gateway.__all__

    def test_single_factory_for_message_signer(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "signer" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_message_signer"

    def test_callable(self):
        assert callable(create_message_signer)

    def test_return_annotation_is_hmac_sha256_signer(self):
        hints = inspect.get_annotations(create_message_signer, eval_str=True)
        assert hints.get("return") is HmacSha256Signer


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_zero_parameters(self):
        sig = inspect.signature(create_message_signer)
        assert len(sig.parameters) == 0

    def test_no_secret_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "secret" not in sig.parameters

    def test_no_api_key_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "api_key" not in sig.parameters

    def test_no_api_secret_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "api_secret" not in sig.parameters

    def test_no_credentials_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "credentials" not in sig.parameters

    def test_no_clock_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "clock" not in sig.parameters

    def test_no_algorithm_parameter(self):
        sig = inspect.signature(create_message_signer)
        assert "algorithm" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_message_signer(object())

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            create_message_signer(secret="demo-secret")


# ---------------------------------------------------------------------------
# 3. Implementación concreta
# ---------------------------------------------------------------------------

class TestConcreteImplementation:
    def test_returns_hmac_sha256_signer(self):
        s = create_message_signer()
        assert isinstance(s, HmacSha256Signer)

    def test_returns_exact_type(self):
        s = create_message_signer()
        assert type(s) is HmacSha256Signer

    def test_satisfies_message_signer_protocol(self):
        s = create_message_signer()
        assert isinstance(s, MessageSigner)

    def test_not_a_protocol_instance_directly(self):
        s = create_message_signer()
        assert type(s) is not MessageSigner

    def test_has_sign_method(self):
        s = create_message_signer()
        assert callable(getattr(s, "sign", None))

    def test_type_name_is_hmac_sha256_signer(self):
        s = create_message_signer()
        assert type(s).__name__ == "HmacSha256Signer"

    def test_not_a_fake(self):
        s = create_message_signer()
        assert not isinstance(s, str)
        assert not isinstance(s, dict)


# ---------------------------------------------------------------------------
# 4. Validación zero-arg
# ---------------------------------------------------------------------------

class TestZeroArgValidation:
    def test_no_positional_arg(self):
        with pytest.raises(TypeError):
            create_message_signer(object())

    def test_no_string_kwarg(self):
        with pytest.raises(TypeError):
            create_message_signer(algorithm="sha256")

    def test_no_bool_kwarg(self):
        with pytest.raises(TypeError):
            create_message_signer(strict=True)


# ---------------------------------------------------------------------------
# 5. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_new_instance_per_call(self):
        s1 = create_message_signer()
        s2 = create_message_signer()
        assert s1 is not s2

    def test_multiple_instances_all_distinct(self):
        instances = [create_message_signer() for _ in range(4)]
        ids = [id(s) for s in instances]
        assert len(set(ids)) == 4

    def test_does_not_return_string(self):
        s = create_message_signer()
        assert not isinstance(s, str)

    def test_does_not_return_bytes(self):
        s = create_message_signer()
        assert not isinstance(s, bytes)

    def test_does_not_return_tuple(self):
        s = create_message_signer()
        assert not isinstance(s, tuple)

    def test_does_not_return_dict(self):
        s = create_message_signer()
        assert not isinstance(s, dict)

    def test_does_not_return_none(self):
        s = create_message_signer()
        assert s is not None

    def test_does_not_return_class(self):
        s = create_message_signer()
        assert not inspect.isclass(s)


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_no_singleton_behavior(self):
        s1 = create_message_signer()
        s2 = create_message_signer()
        assert s1 is not s2

    def test_each_is_hmac_sha256_signer(self):
        for _ in range(3):
            s = create_message_signer()
            assert type(s) is HmacSha256Signer

    def test_each_satisfies_protocol(self):
        for _ in range(3):
            s = create_message_signer()
            assert isinstance(s, MessageSigner)


# ---------------------------------------------------------------------------
# 7. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_sign_call_during_construction(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append((secret, message))
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        create_message_signer()
        assert calls == []

    def test_no_hmac_call_during_construction(self, monkeypatch):
        calls = []
        original_new = _hmac.new

        def spy_new(*args, **kwargs):
            calls.append(args)
            return original_new(*args, **kwargs)

        import hmac as hmac_module
        monkeypatch.setattr(hmac_module, "new", spy_new)
        create_message_signer()
        assert calls == []

    def test_no_network_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_message_signer()
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_SECRET", "sentinel")
        s = create_message_signer()
        assert isinstance(s, HmacSha256Signer)


# ---------------------------------------------------------------------------
# 8. Comportamiento integrado mínimo — semántica criptográfica
# ---------------------------------------------------------------------------

class TestCryptographicBehavior:
    def test_known_vector(self):
        s = create_message_signer()
        result = s.sign(secret="key", message="The quick brown fox jumps over the lazy dog")
        assert result == _expected_hmac("key", "The quick brown fox jumps over the lazy dog")

    def test_output_is_64_char_lowercase_hex(self):
        s = create_message_signer()
        result = s.sign(secret="demo-key", message="payload")
        assert len(result) == 64
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_deterministic_same_inputs(self):
        s = create_message_signer()
        r1 = s.sign(secret="secret", message="message")
        r2 = s.sign(secret="secret", message="message")
        assert r1 == r2

    def test_deterministic_across_instances(self):
        s1 = create_message_signer()
        s2 = create_message_signer()
        assert s1.sign(secret="k", message="v") == s2.sign(secret="k", message="v")

    def test_different_message_different_result(self):
        s = create_message_signer()
        r1 = s.sign(secret="key", message="msg1")
        r2 = s.sign(secret="key", message="msg2")
        assert r1 != r2

    def test_different_secret_different_result(self):
        s = create_message_signer()
        r1 = s.sign(secret="key1", message="msg")
        r2 = s.sign(secret="key2", message="msg")
        assert r1 != r2

    def test_empty_message_accepted(self):
        s = create_message_signer()
        result = s.sign(secret="demo-secret", message="")
        assert result == _expected_hmac("demo-secret", "")

    def test_empty_secret_accepted(self):
        s = create_message_signer()
        result = s.sign(secret="", message="payload")
        assert result == _expected_hmac("", "payload")

    def test_unicode_utf8_encoding(self):
        s = create_message_signer()
        result = s.sign(secret="clavé", message="données")
        assert result == _expected_hmac("clavé", "données")

    def test_returns_str_not_bytes(self):
        s = create_message_signer()
        result = s.sign(secret="demo-secret", message="payload")
        assert isinstance(result, str)

    def test_no_prefix_added(self):
        s = create_message_signer()
        result = s.sign(secret="key", message="msg")
        expected = _expected_hmac("key", "msg")
        assert result == expected

    def test_no_timestamp_in_output(self):
        s = create_message_signer()
        result = s.sign(secret="key", message="msg")
        assert len(result) == 64

    def test_does_not_mutate_secret(self):
        s = create_message_signer()
        secret = "immutable-secret"
        s.sign(secret=secret, message="msg")
        assert secret == "immutable-secret"

    def test_does_not_mutate_message(self):
        s = create_message_signer()
        message = "immutable-message"
        s.sign(secret="key", message=message)
        assert message == "immutable-message"


# ---------------------------------------------------------------------------
# 9. Integración con authenticator
# ---------------------------------------------------------------------------

class TestIntegrationWithAuthenticator:
    def test_signer_accepted_by_create_bybit_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        assert isinstance(auth, StandardBybitAuthenticator)

    def test_signer_identity_preserved_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        assert auth._signer is signer

    def test_credentials_identity_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        assert auth._credentials is credentials

    def test_clock_identity_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = SystemMillisecondClock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        assert auth._clock is clock

    def test_no_sign_during_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        assert calls == []

    def test_no_clock_call_during_composition(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        create_bybit_authenticator(
            credentials=credentials,
            clock=SystemMillisecondClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        assert calls == []


# ---------------------------------------------------------------------------
# 10. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = SystemMillisecondClock()
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
            signer=signer,
            clock=clock,
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

    def test_signer_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._signer is stack["signer"]

    def test_credentials_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._credentials is stack["credentials"]

    def test_clock_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._clock is stack["clock"]

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

    def test_no_sign_during_full_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        self._build_full_stack()
        assert calls == []

    def test_no_clock_during_full_composition(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        self._build_full_stack()
        assert calls == []


# ---------------------------------------------------------------------------
# 11. Seguridad estática
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

    def test_source_does_not_contain_env_var_names(self):
        src = inspect.getsource(_module)
        assert "BYBIT_API_SECRET" not in src
        assert "BYBIT_API_KEY" not in src

    def test_source_does_not_contain_url(self):
        src = inspect.getsource(_module)
        assert "bybit.com" not in src

    def test_source_does_not_contain_literal_secrets(self):
        src = inspect.getsource(_module)
        assert "secret_value" not in src

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)


# ---------------------------------------------------------------------------
# 12. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_does_not_create_authenticator(self):
        src = inspect.getsource(create_message_signer)
        assert "StandardBybitAuthenticator" not in src
        assert "create_bybit_authenticator" not in src
