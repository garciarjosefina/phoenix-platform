import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_recv_window_factory as _module
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer_factory import create_message_signer
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
        from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms as f
        assert f is create_bybit_recv_window_ms

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_recv_window_ms")
        assert execution_gateway.create_bybit_recv_window_ms is create_bybit_recv_window_ms

    def test_included_in_all(self):
        assert "create_bybit_recv_window_ms" in execution_gateway.__all__

    def test_single_factory_for_recv_window(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "recv_window" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_recv_window_ms"

    def test_callable(self):
        assert callable(create_bybit_recv_window_ms)

    def test_return_annotation_is_int(self):
        hints = inspect.get_annotations(create_bybit_recv_window_ms, eval_str=True)
        assert hints.get("return") is int


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert len(sig.parameters) == 1

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        param = sig.parameters["recv_window_ms"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_named_recv_window_ms(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "recv_window_ms" in sig.parameters

    def test_no_credentials_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "credentials" not in sig.parameters

    def test_no_clock_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "clock" not in sig.parameters

    def test_no_signer_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "signer" not in sig.parameters

    def test_no_url_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "url" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_bybit_recv_window_ms)
        assert "environment" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(5_000)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(recv_window_ms=5_000, extra=True)


# ---------------------------------------------------------------------------
# 3. Valores válidos
# ---------------------------------------------------------------------------

class TestValidValues:
    def test_one_is_valid(self):
        assert create_bybit_recv_window_ms(recv_window_ms=1) == 1

    def test_small_positive(self):
        assert create_bybit_recv_window_ms(recv_window_ms=100) == 100

    def test_typical_value(self):
        assert create_bybit_recv_window_ms(recv_window_ms=5_000) == 5_000

    def test_large_value(self):
        assert create_bybit_recv_window_ms(recv_window_ms=60_000) == 60_000

    def test_very_large_value(self):
        assert create_bybit_recv_window_ms(recv_window_ms=10_000_000) == 10_000_000

    def test_max_python_int_accepted(self):
        big = 2**63
        assert create_bybit_recv_window_ms(recv_window_ms=big) == big


# ---------------------------------------------------------------------------
# 4. Valores inválidos — tipo
# ---------------------------------------------------------------------------

class TestTypeValidation:
    def test_bool_true_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: bool"):
            create_bybit_recv_window_ms(recv_window_ms=True)

    def test_bool_false_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: bool"):
            create_bybit_recv_window_ms(recv_window_ms=False)

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: NoneType"):
            create_bybit_recv_window_ms(recv_window_ms=None)

    def test_float_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: float"):
            create_bybit_recv_window_ms(recv_window_ms=5000.0)

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: str"):
            create_bybit_recv_window_ms(recv_window_ms="5000")

    def test_bytes_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(recv_window_ms=b"5000")

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(recv_window_ms=[5000])

    def test_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(recv_window_ms={"ms": 5000})

    def test_object_raises_type_error(self):
        with pytest.raises(TypeError):
            create_bybit_recv_window_ms(recv_window_ms=object())

    def test_type_error_message_for_none(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: NoneType"):
            create_bybit_recv_window_ms(recv_window_ms=None)

    def test_type_error_message_for_float(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: float"):
            create_bybit_recv_window_ms(recv_window_ms=1.5)

    def test_type_error_message_for_str(self):
        with pytest.raises(TypeError, match="recv_window_ms must be int, got: str"):
            create_bybit_recv_window_ms(recv_window_ms="x")


# ---------------------------------------------------------------------------
# 5. Valores inválidos — rango
# ---------------------------------------------------------------------------

class TestRangeValidation:
    def test_zero_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0, got: 0"):
            create_bybit_recv_window_ms(recv_window_ms=0)

    def test_negative_one_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0, got: -1"):
            create_bybit_recv_window_ms(recv_window_ms=-1)

    def test_large_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            create_bybit_recv_window_ms(recv_window_ms=-999_999)

    def test_value_error_message_for_zero(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0, got: 0"):
            create_bybit_recv_window_ms(recv_window_ms=0)


# ---------------------------------------------------------------------------
# 6. Subclasses de int
# ---------------------------------------------------------------------------

class TestIntSubclass:
    def test_int_subclass_accepted(self):
        class MyInt(int):
            pass

        result = create_bybit_recv_window_ms(recv_window_ms=MyInt(5_000))
        assert result == 5_000

    def test_int_subclass_not_converted(self):
        class MyInt(int):
            pass

        val = MyInt(7_000)
        result = create_bybit_recv_window_ms(recv_window_ms=val)
        assert result == 7_000


# ---------------------------------------------------------------------------
# 7. Ausencia de transformación
# ---------------------------------------------------------------------------

class TestNoTransformation:
    def test_value_preserved_exactly(self):
        assert create_bybit_recv_window_ms(recv_window_ms=3_333) == 3_333

    def test_value_not_converted_to_float(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert isinstance(result, int)
        assert not isinstance(result, float)

    def test_value_not_converted_to_string(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert isinstance(result, int)

    def test_result_type_is_int(self):
        result = create_bybit_recv_window_ms(recv_window_ms=1_234)
        assert type(result) is int or isinstance(result, int)

    def test_no_rounding_applied(self):
        assert create_bybit_recv_window_ms(recv_window_ms=9_999) == 9_999

    def test_no_clamping_applied(self):
        assert create_bybit_recv_window_ms(recv_window_ms=999_999) == 999_999

    def test_does_not_return_bool(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert not isinstance(result, bool)

    def test_does_not_return_none(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert result is not None

    def test_does_not_return_tuple(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert not isinstance(result, tuple)

    def test_does_not_return_dict(self):
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert not isinstance(result, dict)


# ---------------------------------------------------------------------------
# 8. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_same_value_each_call(self):
        r1 = create_bybit_recv_window_ms(recv_window_ms=5_000)
        r2 = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert r1 == r2

    def test_no_state_accumulation(self):
        for _ in range(5):
            result = create_bybit_recv_window_ms(recv_window_ms=1_000)
            assert result == 1_000

    def test_independent_calls_different_values(self):
        r1 = create_bybit_recv_window_ms(recv_window_ms=1_000)
        r2 = create_bybit_recv_window_ms(recv_window_ms=2_000)
        assert r1 == 1_000
        assert r2 == 2_000


# ---------------------------------------------------------------------------
# 9. Ausencia de ejecución
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_no_network_during_construction(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_recv_window_ms(recv_window_ms=5_000)
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_env_vars_read(self, monkeypatch):
        monkeypatch.setenv("BYBIT_RECV_WINDOW", "9999")
        result = create_bybit_recv_window_ms(recv_window_ms=5_000)
        assert result == 5_000


# ---------------------------------------------------------------------------
# 10. Seguridad estática
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

    def test_does_not_import_authenticator(self):
        assert "StandardBybitAuthenticator" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_does_not_import_signer(self):
        assert "MessageSigner" not in vars(_module)
        assert "HmacSha256Signer" not in vars(_module)

    def test_does_not_import_clock(self):
        assert "MillisecondClock" not in vars(_module)
        assert "SystemMillisecondClock" not in vars(_module)


# ---------------------------------------------------------------------------
# 11. Integración con authenticator
# ---------------------------------------------------------------------------

class TestIntegrationWithAuthenticator:
    def test_recv_window_accepted_by_authenticator(self):
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert isinstance(auth, StandardBybitAuthenticator)

    def test_recv_window_preserved_in_authenticator(self):
        recv = create_bybit_recv_window_ms(recv_window_ms=7_777)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert auth._recv_window_ms == 7_777

    def test_credentials_identity_in_authenticator(self):
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert auth._credentials is credentials

    def test_signer_identity_in_authenticator(self):
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert auth._signer is signer

    def test_clock_identity_in_authenticator(self):
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        auth = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert auth._clock is clock

    def test_no_clock_call_during_composition(self, monkeypatch):
        calls = []
        original_now = SystemMillisecondClock.now_ms

        def spy_now(self):
            calls.append(True)
            return original_now(self)

        monkeypatch.setattr(SystemMillisecondClock, "now_ms", spy_now)
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert calls == []

    def test_no_sign_during_composition(self, monkeypatch):
        calls = []
        original_sign = HmacSha256Signer.sign

        def spy_sign(self, *, secret, message):
            calls.append(True)
            return original_sign(self, secret=secret, message=message)

        monkeypatch.setattr(HmacSha256Signer, "sign", spy_sign)
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        assert calls == []


# ---------------------------------------------------------------------------
# 12. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self, recv_window_ms: int = 5_000):
        recv = create_bybit_recv_window_ms(recv_window_ms=recv_window_ms)
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        authenticator = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
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
            recv=recv,
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

    def test_recv_window_preserved_in_authenticator(self):
        stack = self._build_full_stack(recv_window_ms=3_000)
        assert stack["authenticator"]._recv_window_ms == 3_000

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
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            self._build_full_stack()
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_clock_during_full_composition(self, monkeypatch):
        import time
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
# 13. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_does_not_create_authenticator(self):
        src = inspect.getsource(create_bybit_recv_window_ms)
        assert "StandardBybitAuthenticator" not in src

    def test_does_not_create_signer(self):
        src = inspect.getsource(create_bybit_recv_window_ms)
        assert "HmacSha256Signer" not in src

    def test_does_not_create_clock(self):
        src = inspect.getsource(create_bybit_recv_window_ms)
        assert "SystemMillisecondClock" not in src
