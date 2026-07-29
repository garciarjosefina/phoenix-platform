import inspect
import math

import pytest

import execution_gateway
import execution_gateway.http_timeout_factory as _module
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
from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.millisecond_clock_factory import create_millisecond_clock
from execution_gateway.system_millisecond_clock import SystemMillisecondClock
from execution_gateway.urllib_http_transport import UrllibHttpTransport


_VALID_KEY = "demo-key"
_VALID_SECRET = "demo-secret"


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.http_timeout_factory import create_http_timeout_seconds as f
        assert f is create_http_timeout_seconds

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_http_timeout_seconds")
        assert execution_gateway.create_http_timeout_seconds is create_http_timeout_seconds

    def test_included_in_all(self):
        assert "create_http_timeout_seconds" in execution_gateway.__all__

    def test_single_factory_for_timeout(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "timeout" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_http_timeout_seconds"

    def test_callable(self):
        assert callable(create_http_timeout_seconds)

    def test_return_annotation(self):
        hints = inspect.get_annotations(create_http_timeout_seconds, eval_str=True)
        ret = hints.get("return")
        # accepts int | float — verify both int and float are represented
        assert int in (ret.__args__ if hasattr(ret, "__args__") else (ret,))
        assert float in (ret.__args__ if hasattr(ret, "__args__") else (ret,))


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_exactly_one_parameter(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert len(sig.parameters) == 1

    def test_parameter_is_keyword_only(self):
        sig = inspect.signature(create_http_timeout_seconds)
        param = sig.parameters["timeout_seconds"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_parameter_named_timeout_seconds(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert "timeout_seconds" in sig.parameters

    def test_no_transport_parameter(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert "transport" not in sig.parameters

    def test_no_url_parameter(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert "url" not in sig.parameters

    def test_no_retries_parameter(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert "retries" not in sig.parameters

    def test_no_environment_parameter(self):
        sig = inspect.signature(create_http_timeout_seconds)
        assert "environment" not in sig.parameters

    def test_no_positional_args_accepted(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(5.0)

    def test_no_unknown_kwargs_accepted(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(timeout_seconds=5.0, extra=True)


# ---------------------------------------------------------------------------
# 3. Valores válidos — int
# ---------------------------------------------------------------------------

class TestValidInt:
    def test_int_one_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=1) == 1

    def test_int_ten_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=10) == 10

    def test_int_large_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=3_600) == 3_600

    def test_int_preserved_as_int(self):
        result = create_http_timeout_seconds(timeout_seconds=5)
        assert type(result) is int

    def test_int_not_converted_to_float(self):
        result = create_http_timeout_seconds(timeout_seconds=5)
        assert not isinstance(result, float)


# ---------------------------------------------------------------------------
# 4. Valores válidos — float
# ---------------------------------------------------------------------------

class TestValidFloat:
    def test_float_point_one_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=0.1) == 0.1

    def test_float_five_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=5.0) == 5.0

    def test_float_large_valid(self):
        assert create_http_timeout_seconds(timeout_seconds=300.5) == 300.5

    def test_float_preserved_as_float(self):
        result = create_http_timeout_seconds(timeout_seconds=5.0)
        assert type(result) is float

    def test_float_not_converted_to_int(self):
        result = create_http_timeout_seconds(timeout_seconds=2.5)
        assert not isinstance(result, int)


# ---------------------------------------------------------------------------
# 5. Valores inválidos — tipo
# ---------------------------------------------------------------------------

class TestTypeValidation:
    def test_bool_true_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: bool"):
            create_http_timeout_seconds(timeout_seconds=True)

    def test_bool_false_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: bool"):
            create_http_timeout_seconds(timeout_seconds=False)

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: NoneType"):
            create_http_timeout_seconds(timeout_seconds=None)

    def test_string_raises_type_error(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: str"):
            create_http_timeout_seconds(timeout_seconds="5.0")

    def test_bytes_raises_type_error(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(timeout_seconds=b"5.0")

    def test_list_raises_type_error(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(timeout_seconds=[5.0])

    def test_dict_raises_type_error(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(timeout_seconds={"seconds": 5})

    def test_object_raises_type_error(self):
        with pytest.raises(TypeError):
            create_http_timeout_seconds(timeout_seconds=object())

    def test_type_error_message_for_none(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: NoneType"):
            create_http_timeout_seconds(timeout_seconds=None)

    def test_type_error_message_for_string(self):
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: str"):
            create_http_timeout_seconds(timeout_seconds="5")


# ---------------------------------------------------------------------------
# 6. Valores inválidos — rango
# ---------------------------------------------------------------------------

class TestRangeValidation:
    def test_zero_int_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0, got: 0"):
            create_http_timeout_seconds(timeout_seconds=0)

    def test_zero_float_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0, got: 0.0"):
            create_http_timeout_seconds(timeout_seconds=0.0)

    def test_negative_int_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_timeout_seconds(timeout_seconds=-1)

    def test_negative_float_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_timeout_seconds(timeout_seconds=-0.1)

    def test_large_negative_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_timeout_seconds(timeout_seconds=-999)

    def test_value_error_message_for_zero(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0, got: 0"):
            create_http_timeout_seconds(timeout_seconds=0)

    def test_negative_infinity_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_timeout_seconds(timeout_seconds=float("-inf"))


# ---------------------------------------------------------------------------
# 7. NaN e infinito — comportamiento productivo exacto
# ---------------------------------------------------------------------------

class TestNanAndInfinity:
    def test_nan_accepted(self):
        result = create_http_timeout_seconds(timeout_seconds=math.nan)
        assert math.isnan(result)

    def test_positive_infinity_accepted(self):
        result = create_http_timeout_seconds(timeout_seconds=math.inf)
        assert math.isinf(result) and result > 0

    def test_negative_infinity_raises_value_error(self):
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_http_timeout_seconds(timeout_seconds=-math.inf)


# ---------------------------------------------------------------------------
# 8. Decimal y Fraction
# ---------------------------------------------------------------------------

class TestDecimalAndFraction:
    def test_decimal_raises_type_error(self):
        from decimal import Decimal
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: Decimal"):
            create_http_timeout_seconds(timeout_seconds=Decimal("5.0"))

    def test_fraction_raises_type_error(self):
        from fractions import Fraction
        with pytest.raises(TypeError, match="timeout_seconds must be int or float, got: Fraction"):
            create_http_timeout_seconds(timeout_seconds=Fraction(5, 1))


# ---------------------------------------------------------------------------
# 9. Subclasses
# ---------------------------------------------------------------------------

class TestSubclasses:
    def test_int_subclass_accepted(self):
        class MyInt(int):
            pass
        result = create_http_timeout_seconds(timeout_seconds=MyInt(5))
        assert result == 5

    def test_float_subclass_accepted(self):
        class MyFloat(float):
            pass
        result = create_http_timeout_seconds(timeout_seconds=MyFloat(5.0))
        assert result == 5.0

    def test_bool_subclass_rejected(self):
        with pytest.raises(TypeError, match="bool"):
            create_http_timeout_seconds(timeout_seconds=True)


# ---------------------------------------------------------------------------
# 10. Ausencia de transformación
# ---------------------------------------------------------------------------

class TestNoTransformation:
    def test_int_value_preserved_exactly(self):
        assert create_http_timeout_seconds(timeout_seconds=7) == 7

    def test_float_value_preserved_exactly(self):
        assert create_http_timeout_seconds(timeout_seconds=3.14) == pytest.approx(3.14)

    def test_int_not_cast_to_float(self):
        result = create_http_timeout_seconds(timeout_seconds=10)
        assert isinstance(result, int)

    def test_float_not_cast_to_int(self):
        result = create_http_timeout_seconds(timeout_seconds=2.7)
        assert isinstance(result, float)

    def test_no_rounding(self):
        assert create_http_timeout_seconds(timeout_seconds=1.999) == pytest.approx(1.999)

    def test_no_clamping(self):
        assert create_http_timeout_seconds(timeout_seconds=999_999) == 999_999

    def test_does_not_return_bool(self):
        result = create_http_timeout_seconds(timeout_seconds=5)
        assert not isinstance(result, bool)

    def test_does_not_return_none(self):
        result = create_http_timeout_seconds(timeout_seconds=5.0)
        assert result is not None

    def test_does_not_return_tuple(self):
        result = create_http_timeout_seconds(timeout_seconds=5.0)
        assert not isinstance(result, tuple)

    def test_does_not_return_dict(self):
        result = create_http_timeout_seconds(timeout_seconds=5.0)
        assert not isinstance(result, dict)


# ---------------------------------------------------------------------------
# 11. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_same_value_each_call(self):
        r1 = create_http_timeout_seconds(timeout_seconds=5.0)
        r2 = create_http_timeout_seconds(timeout_seconds=5.0)
        assert r1 == r2

    def test_no_state_accumulation(self):
        for _ in range(5):
            result = create_http_timeout_seconds(timeout_seconds=1.0)
            assert result == 1.0

    def test_independent_calls_different_values(self):
        r1 = create_http_timeout_seconds(timeout_seconds=1.0)
        r2 = create_http_timeout_seconds(timeout_seconds=2.0)
        assert r1 == 1.0
        assert r2 == 2.0


# ---------------------------------------------------------------------------
# 12. Ausencia de ejecución
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
            create_http_timeout_seconds(timeout_seconds=5.0)
        finally:
            socket.socket.connect = original
        assert calls == []

    def test_no_env_vars_read(self, monkeypatch):
        monkeypatch.setenv("HTTP_TIMEOUT", "9999")
        result = create_http_timeout_seconds(timeout_seconds=5.0)
        assert result == 5.0


# ---------------------------------------------------------------------------
# 13. Seguridad estática
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
        assert "BYBIT_" not in src
        assert "HTTP_TIMEOUT" not in src

    def test_source_does_not_contain_url(self):
        src = inspect.getsource(_module)
        assert "bybit.com" not in src

    def test_does_not_import_transport(self):
        assert "HttpTransport" not in vars(_module)
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_import_executor(self):
        assert "HttpRequestExecutor" not in vars(_module)


# ---------------------------------------------------------------------------
# 14. Integración con executor
# ---------------------------------------------------------------------------

class TestIntegrationWithExecutor:
    def test_timeout_accepted_by_executor(self):
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=5.0)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        assert isinstance(executor, HttpRequestExecutor)

    def test_timeout_preserved_in_executor(self):
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=7.5)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        assert executor._timeout_seconds == 7.5

    def test_transport_identity_in_executor(self):
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=5.0)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        assert executor._transport is transport

    def test_int_timeout_preserved_in_executor(self):
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=10)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout)
        assert executor._timeout_seconds == 10

    def test_no_http_during_composition(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        transport = create_http_transport()
        timeout = create_http_timeout_seconds(timeout_seconds=5.0)
        create_http_request_executor(transport=transport, timeout_seconds=timeout)
        assert calls == []


# ---------------------------------------------------------------------------
# 15. Integración completa sin ejecución
# ---------------------------------------------------------------------------

class TestFullIntegrationNoExecution:
    def _build_full_stack(self, timeout: float = 5.0):
        credentials = create_bybit_demo_credentials(api_key=_VALID_KEY, api_secret=_VALID_SECRET)
        signer = create_message_signer()
        clock = create_millisecond_clock()
        recv = create_bybit_recv_window_ms(recv_window_ms=5_000)
        authenticator = create_bybit_authenticator(
            credentials=credentials,
            clock=clock,
            signer=signer,
            recv_window_ms=recv,
        )
        serializer = create_json_serializer()
        header_builder = create_bybit_header_builder()
        request_builder = create_bybit_request_builder(
            serializer=serializer,
            authenticator=authenticator,
            header_builder=header_builder,
        )
        parser = create_bybit_response_parser(serializer=serializer)
        transport = create_http_transport()
        timeout_val = create_http_timeout_seconds(timeout_seconds=timeout)
        executor = create_http_request_executor(transport=transport, timeout_seconds=timeout_val)
        sender = create_bybit_private_request_sender(
            request_builder=request_builder,
            request_executor=executor,
        )
        private_api = create_bybit_private_api(sender=sender, response_parser=parser)
        gateway = create_bybit_demo_execution_gateway(private_api=private_api)

        return dict(
            credentials=credentials,
            signer=signer,
            clock=clock,
            authenticator=authenticator,
            serializer=serializer,
            header_builder=header_builder,
            request_builder=request_builder,
            parser=parser,
            transport=transport,
            timeout_val=timeout_val,
            executor=executor,
            sender=sender,
            private_api=private_api,
            gateway=gateway,
        )

    def test_full_stack_builds_successfully(self):
        stack = self._build_full_stack()
        assert isinstance(stack["gateway"], BybitExecutionGateway)

    def test_timeout_preserved_in_executor(self):
        stack = self._build_full_stack(timeout=8.8)
        assert stack["executor"]._timeout_seconds == pytest.approx(8.8)

    def test_transport_identity_in_executor(self):
        stack = self._build_full_stack()
        assert stack["executor"]._transport is stack["transport"]

    def test_executor_identity_in_sender(self):
        stack = self._build_full_stack()
        assert stack["sender"]._request_executor is stack["executor"]

    def test_serializer_shared_in_builder_and_parser(self):
        stack = self._build_full_stack()
        assert stack["request_builder"]._serializer is stack["serializer"]
        assert stack["parser"]._serializer is stack["serializer"]

    def test_credentials_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._credentials is stack["credentials"]

    def test_signer_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._signer is stack["signer"]

    def test_clock_identity_in_authenticator(self):
        stack = self._build_full_stack()
        assert stack["authenticator"]._clock is stack["clock"]

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

    def test_no_http_during_full_composition(self, monkeypatch):
        calls = []
        original_post = UrllibHttpTransport.post

        def spy_post(self, *, url, headers, body, timeout_seconds):
            calls.append(url)
            return original_post(self, url=url, headers=headers, body=body, timeout_seconds=timeout_seconds)

        monkeypatch.setattr(UrllibHttpTransport, "post", spy_post)
        self._build_full_stack()
        assert calls == []


# ---------------------------------------------------------------------------
# 16. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_full_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_does_not_create_transport(self):
        src = inspect.getsource(create_http_timeout_seconds)
        assert "UrllibHttpTransport" not in src
        assert "HttpTransport" not in src

    def test_does_not_create_executor(self):
        src = inspect.getsource(create_http_timeout_seconds)
        assert "HttpRequestExecutor" not in src
