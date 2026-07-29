import inspect
import time

import pytest

import execution_gateway
import execution_gateway.millisecond_clock_factory as _module
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
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.millisecond_clock import MillisecondClock
from execution_gateway.millisecond_clock_factory import create_millisecond_clock
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.system_millisecond_clock import SystemMillisecondClock


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.millisecond_clock_factory import create_millisecond_clock as f
        assert f is create_millisecond_clock

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_millisecond_clock")
        assert execution_gateway.create_millisecond_clock is create_millisecond_clock

    def test_included_in_all(self):
        assert "create_millisecond_clock" in execution_gateway.__all__

    def test_single_factory_for_millisecond_clock(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "clock" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_millisecond_clock"

    def test_callable(self):
        assert callable(create_millisecond_clock)

    def test_return_annotation_is_system_millisecond_clock(self):
        hints = inspect.get_annotations(create_millisecond_clock, eval_str=True)
        assert hints.get("return") is SystemMillisecondClock


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_zero_parameters(self):
        sig = inspect.signature(create_millisecond_clock)
        assert len(sig.parameters) == 0

    def test_no_timezone_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "timezone" not in sig.parameters

    def test_no_offset_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "offset" not in sig.parameters

    def test_no_credentials_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "credentials" not in sig.parameters

    def test_no_signer_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "signer" not in sig.parameters

    def test_no_secret_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "secret" not in sig.parameters

    def test_no_url_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "url" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "environment" not in sig.parameters

    def test_no_recv_window_parameter(self):
        sig = inspect.signature(create_millisecond_clock)
        assert "recv_window_ms" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_millisecond_clock(object())

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            create_millisecond_clock(timezone="UTC")


# ---------------------------------------------------------------------------
# 3. Implementación concreta
# ---------------------------------------------------------------------------

class TestConcreteImplementation:
    def test_returns_system_millisecond_clock(self):
        c = create_millisecond_clock()
        assert isinstance(c, SystemMillisecondClock)

    def test_returns_exact_type(self):
        c = create_millisecond_clock()
        assert type(c) is SystemMillisecondClock

    def test_satisfies_millisecond_clock_protocol(self):
        c = create_millisecond_clock()
        assert isinstance(c, MillisecondClock)

    def test_has_now_ms_method(self):
        c = create_millisecond_clock()
        assert callable(getattr(c, "now_ms", None))

    def test_type_name_is_system_millisecond_clock(self):
        c = create_millisecond_clock()
        assert type(c).__name__ == "SystemMillisecondClock"

    def test_not_a_protocol_instance_directly(self):
        c = create_millisecond_clock()
        assert type(c) is not MillisecondClock

    def test_not_an_int(self):
        c = create_millisecond_clock()
        assert not isinstance(c, int)


# ---------------------------------------------------------------------------
# 4. Validación zero-arg
# ---------------------------------------------------------------------------

class TestZeroArgValidation:
    def test_no_positional_arg(self):
        with pytest.raises(TypeError):
            create_millisecond_clock(object())

    def test_no_string_kwarg(self):
        with pytest.raises(TypeError):
            create_millisecond_clock(timezone="UTC")

    def test_no_int_kwarg(self):
        with pytest.raises(TypeError):
            create_millisecond_clock(offset=0)


# ---------------------------------------------------------------------------
# 5. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_new_instance_per_call(self):
        c1 = create_millisecond_clock()
        c2 = create_millisecond_clock()
        assert c1 is not c2

    def test_multiple_instances_all_distinct(self):
        instances = [create_millisecond_clock() for _ in range(4)]
        ids = [id(c) for c in instances]
        assert len(set(ids)) == 4

    def test_does_not_return_int(self):
        c = create_millisecond_clock()
        assert not isinstance(c, int)

    def test_does_not_return_float(self):
        c = create_millisecond_clock()
        assert not isinstance(c, float)

    def test_does_not_return_tuple(self):
        c = create_millisecond_clock()
        assert not isinstance(c, tuple)

    def test_does_not_return_dict(self):
        c = create_millisecond_clock()
        assert not isinstance(c, dict)

    def test_does_not_return_none(self):
        c = create_millisecond_clock()
        assert c is not None

    def test_does_not_return_class(self):
        c = create_millisecond_clock()
        assert not inspect.isclass(c)


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_no_singleton(self):
        c1 = create_millisecond_clock()
        c2 = create_millisecond_clock()
        assert c1 is not c2

    def test_each_is_system_millisecond_clock(self):
        for _ in range(3):
            c = create_millisecond_clock()
            assert type(c) is SystemMillisecondClock

    def test_each_satisfies_protocol(self):
        for _ in range(3):
            c = create_millisecond_clock()
            assert isinstance(c, MillisecondClock)


# ---------------------------------------------------------------------------
# 7. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_time_ns_call_during_construction(self, monkeypatch):
        calls = []
        original = time.time_ns

        def spy_time_ns():
            calls.append(True)
            return original()

        monkeypatch.setattr(time, "time_ns", spy_time_ns)
        create_millisecond_clock()
        assert calls == []

    def test_no_now_ms_call_during_construction(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        create_millisecond_clock()
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
            create_millisecond_clock()
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        c = create_millisecond_clock()
        assert isinstance(c, SystemMillisecondClock)


# ---------------------------------------------------------------------------
# 8. Comportamiento integrado mínimo — semántica temporal
# ---------------------------------------------------------------------------

class TestTemporalBehavior:
    def test_now_ms_returns_int(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_700_000_000_000_000_000)
        c = create_millisecond_clock()
        assert isinstance(c.now_ms(), int)

    def test_now_ms_converts_ns_to_ms_truncation(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_700_000_000_000_000_000)
        c = create_millisecond_clock()
        assert c.now_ms() == 1_700_000_000_000

    def test_truncates_not_rounds(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_700_000_000_000_999_999)
        c = create_millisecond_clock()
        assert c.now_ms() == 1_700_000_000_000

    def test_exact_millisecond_boundary(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_000_000)
        c = create_millisecond_clock()
        assert c.now_ms() == 1

    def test_zero_ns(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 0)
        c = create_millisecond_clock()
        assert c.now_ms() == 0

    def test_deterministic_under_controlled_source(self, monkeypatch):
        fixed_ns = 9_999_999_999_000_000_000
        monkeypatch.setattr(time, "time_ns", lambda: fixed_ns)
        c = create_millisecond_clock()
        assert c.now_ms() == c.now_ms()

    def test_successive_calls_reflect_source(self, monkeypatch):
        counter = [1_000_000_000_000_000_000]

        def advancing():
            val = counter[0]
            counter[0] += 1_000_000
            return val

        monkeypatch.setattr(time, "time_ns", advancing)
        c = create_millisecond_clock()
        t1 = c.now_ms()
        t2 = c.now_ms()
        assert t2 > t1

    def test_no_offset_added(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 5_000_000_000)
        c = create_millisecond_clock()
        assert c.now_ms() == 5_000

    def test_unix_epoch_reference(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 0)
        c = create_millisecond_clock()
        assert c.now_ms() == 0

    def test_large_timestamp(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 9_999_999_999_999_000_000)
        c = create_millisecond_clock()
        assert c.now_ms() == 9_999_999_999_999

    def test_result_is_not_none(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_000_000_000_000_000)
        c = create_millisecond_clock()
        assert c.now_ms() is not None

    def test_result_is_not_float(self, monkeypatch):
        monkeypatch.setattr(time, "time_ns", lambda: 1_500_000_000_000_000_000)
        c = create_millisecond_clock()
        assert isinstance(c.now_ms(), int)
        assert not isinstance(c.now_ms(), float)


# ---------------------------------------------------------------------------
# 9. Integración con authenticator
# ---------------------------------------------------------------------------

class TestIntegrationWithAuthenticator:
    def test_clock_accepted_by_create_bybit_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        assert isinstance(auth, StandardBybitAuthenticator)

    def test_clock_identity_preserved_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        assert auth._clock is clock

    def test_signer_identity_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        assert auth._signer is signer

    def test_credentials_identity_in_authenticator(self):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
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
        signer = create_message_signer()
        clock = create_millisecond_clock()
        create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=5_000,
        )
        assert calls == []

    def test_no_sign_during_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
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
        clock = create_millisecond_clock()
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

    def test_clock_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._clock is stack["clock"]

    def test_signer_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._signer is stack["signer"]

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

    def test_no_clock_during_full_composition(self, monkeypatch):
        calls = []
        original_ns = time.time_ns

        def spy_ns():
            calls.append(True)
            return original_ns()

        monkeypatch.setattr(time, "time_ns", spy_ns)
        self._build_full_stack()
        assert calls == []

    def test_no_sign_during_full_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
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
        assert "BYBIT_API_KEY" not in src
        assert "BYBIT_API_SECRET" not in src

    def test_source_does_not_contain_url(self):
        src = inspect.getsource(_module)
        assert "bybit.com" not in src

    def test_source_does_not_call_time_directly(self):
        src = inspect.getsource(create_millisecond_clock)
        assert "time_ns" not in src
        assert "time.time" not in src
        assert "datetime" not in src

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "MessageSigner" not in vars(_module)
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_import_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)


# ---------------------------------------------------------------------------
# 12. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_does_not_create_authenticator(self):
        src = inspect.getsource(create_millisecond_clock)
        assert "StandardBybitAuthenticator" not in src
        assert "create_bybit_authenticator" not in src

    def test_does_not_create_signer(self):
        src = inspect.getsource(create_millisecond_clock)
        assert "HmacSha256Signer" not in src
