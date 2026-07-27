import inspect

import pytest

import execution_gateway
import execution_gateway.bybit_authenticator_factory as _module
from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.http_request import HttpRequest
from execution_gateway.message_signer import MessageSigner
from execution_gateway.millisecond_clock import MillisecondClock
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_credentials(
    api_key: str = "test_api_key",
    api_secret: str = "test_api_secret",
) -> BybitDemoCredentials:
    return BybitDemoCredentials(api_key=api_key, api_secret=api_secret)


def _make_authenticator() -> StandardBybitAuthenticator:
    return create_bybit_authenticator(
        credentials=_make_credentials(),
        clock=SpyClock(),
        signer=SpySigner(),
        recv_window_ms=5_000,
    )


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyClock:
    def __init__(self, result: int = 1_700_000_000_000):
        self.calls: list = []
        self._result = result

    def now_ms(self) -> int:
        self.calls.append({})
        return self._result


class SpySigner:
    def __init__(self, result: str = "abcdef0123456789" * 4):
        self.calls: list[dict] = []
        self._result = result

    def sign(self, *, secret: str, message: str) -> str:
        self.calls.append({"secret": secret, "message": message})
        return self._result


class RaisingClock:
    def __init__(self, error: Exception):
        self._error = error
        self.call_count = 0

    def now_ms(self) -> int:
        self.call_count += 1
        raise self._error


class RaisingSigner:
    def __init__(self, error: Exception):
        self._error = error
        self.call_count = 0

    def sign(self, *, secret: str, message: str) -> str:
        self.call_count += 1
        raise self._error


class SpyHeaderBuilder(BybitHeaderBuilder):
    def __init__(self):
        self.calls: list[dict] = []

    def build(self, *, authentication: BybitAuthentication) -> dict[str, str]:
        self.calls.append({"authentication": authentication})
        return super().build(authentication=authentication)


class SpySerializer:
    def dumps(self, v): return "{}"
    def loads(self, v): return {}


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_authenticator_factory import (
            create_bybit_authenticator as f,
        )
        assert f is create_bybit_authenticator

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_authenticator")
        assert execution_gateway.create_bybit_authenticator is create_bybit_authenticator

    def test_included_in_all(self):
        assert "create_bybit_authenticator" in execution_gateway.__all__

    def test_single_factory_for_bybit_authenticator(self):
        factory_names = [
            name for name in vars(_module)
            if inspect.isfunction(getattr(_module, name))
            and "authenticator" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_authenticator"

    def test_positional_call_rejected(self):
        with pytest.raises(TypeError):
            create_bybit_authenticator(
                _make_credentials(), SpyClock(), SpySigner(), 5_000
            )

    def test_all_params_keyword_only(self):
        sig = inspect.signature(create_bybit_authenticator)
        for name, param in sig.parameters.items():
            assert param.kind == inspect.Parameter.KEYWORD_ONLY

    def test_return_annotation_is_standard_bybit_authenticator(self):
        hints = inspect.get_annotations(create_bybit_authenticator, eval_str=True)
        assert hints.get("return") is StandardBybitAuthenticator


# ---------------------------------------------------------------------------
# 2. Firma exacta
# ---------------------------------------------------------------------------

class TestSignature:
    def test_has_credentials_param(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "credentials" in sig.parameters

    def test_has_clock_param(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "clock" in sig.parameters

    def test_has_signer_param(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "signer" in sig.parameters

    def test_has_recv_window_ms_param(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "recv_window_ms" in sig.parameters

    def test_exactly_four_params(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert len(sig.parameters) == 4

    def test_does_not_receive_api_key(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "api_key" not in sig.parameters

    def test_does_not_receive_api_secret(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "api_secret" not in sig.parameters

    def test_does_not_receive_base_url(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert "base_url" not in sig.parameters

    def test_no_default_for_credentials(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert sig.parameters["credentials"].default is inspect.Parameter.empty

    def test_no_default_for_clock(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert sig.parameters["clock"].default is inspect.Parameter.empty

    def test_no_default_for_signer(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert sig.parameters["signer"].default is inspect.Parameter.empty

    def test_no_default_for_recv_window_ms(self):
        sig = inspect.signature(create_bybit_authenticator)
        assert sig.parameters["recv_window_ms"].default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Validación — credentials
# ---------------------------------------------------------------------------

class TestValidationCredentials:
    def test_accepts_valid_credentials(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert a is not None

    def test_accepts_bybit_demo_credentials_instance(self):
        a = create_bybit_authenticator(
            credentials=BybitDemoCredentials(api_key="key", api_secret="secret"),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_rejects_none_credentials(self):
        with pytest.raises(TypeError, match="BybitDemoCredentials"):
            create_bybit_authenticator(
                credentials=None,
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_dict_credentials(self):
        with pytest.raises(TypeError, match="BybitDemoCredentials"):
            create_bybit_authenticator(
                credentials={"api_key": "k", "api_secret": "s"},
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_string_credentials(self):
        with pytest.raises(TypeError, match="BybitDemoCredentials"):
            create_bybit_authenticator(
                credentials="api_key:secret",
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_arbitrary_object(self):
        with pytest.raises(TypeError, match="BybitDemoCredentials"):
            create_bybit_authenticator(
                credentials=object(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_error_message_contains_type_name(self):
        with pytest.raises(TypeError, match="int"):
            create_bybit_authenticator(
                credentials=42,
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )


# ---------------------------------------------------------------------------
# 4. Validación — clock
# ---------------------------------------------------------------------------

class TestValidationClock:
    def test_accepts_valid_clock(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert a is not None

    def test_accepts_structural_clock(self):
        class AnonClock:
            def now_ms(self) -> int:
                return 0
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=AnonClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_accepts_system_millisecond_clock(self):
        from execution_gateway.system_millisecond_clock import SystemMillisecondClock
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SystemMillisecondClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_rejects_none_clock(self):
        with pytest.raises(TypeError, match="MillisecondClock"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=None,
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_dict_clock(self):
        with pytest.raises(TypeError, match="MillisecondClock"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock={"now_ms": None},
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_string_clock(self):
        with pytest.raises(TypeError, match="MillisecondClock"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock="clock",
                signer=SpySigner(),
                recv_window_ms=5_000,
            )

    def test_rejects_object_without_now_ms(self):
        with pytest.raises(TypeError, match="MillisecondClock"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=object(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )


# ---------------------------------------------------------------------------
# 5. Validación — signer
# ---------------------------------------------------------------------------

class TestValidationSigner:
    def test_accepts_valid_signer(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert a is not None

    def test_accepts_structural_signer(self):
        class AnonSigner:
            def sign(self, *, secret: str, message: str) -> str:
                return "abc"
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=AnonSigner(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_accepts_hmac_sha256_signer(self):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=HmacSha256Signer(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_rejects_none_signer(self):
        with pytest.raises(TypeError, match="MessageSigner"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=None,
                recv_window_ms=5_000,
            )

    def test_rejects_dict_signer(self):
        with pytest.raises(TypeError, match="MessageSigner"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer={"sign": None},
                recv_window_ms=5_000,
            )

    def test_rejects_string_signer(self):
        with pytest.raises(TypeError, match="MessageSigner"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer="hmac",
                recv_window_ms=5_000,
            )

    def test_rejects_object_without_sign(self):
        with pytest.raises(TypeError, match="MessageSigner"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=object(),
                recv_window_ms=5_000,
            )


# ---------------------------------------------------------------------------
# 6. Validación — recv_window_ms
# ---------------------------------------------------------------------------

class TestValidationRecvWindowMs:
    def test_accepts_positive_int(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert a is not None

    def test_accepts_1(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=1,
        )
        assert isinstance(a, StandardBybitAuthenticator)

    def test_rejects_zero(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=0,
            )

    def test_rejects_negative(self):
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=-1,
            )

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="recv_window_ms"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=None,
            )

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="recv_window_ms"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000.0,
            )

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="recv_window_ms"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms="5000",
            )

    def test_rejects_bool_true(self):
        with pytest.raises(TypeError, match="recv_window_ms"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=True,
            )

    def test_rejects_bool_false(self):
        with pytest.raises(TypeError, match="recv_window_ms"):
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=False,
            )


# ---------------------------------------------------------------------------
# 7. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_standard_bybit_authenticator(self):
        a = _make_authenticator()
        assert isinstance(a, StandardBybitAuthenticator)

    def test_returns_exact_type(self):
        a = _make_authenticator()
        assert type(a) is StandardBybitAuthenticator

    def test_two_calls_return_different_authenticators(self):
        creds = _make_credentials()
        clock = SpyClock()
        signer = SpySigner()
        a1 = create_bybit_authenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5_000
        )
        a2 = create_bybit_authenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5_000
        )
        assert a1 is not a2

    def test_does_not_return_tuple(self):
        a = _make_authenticator()
        assert not isinstance(a, tuple)

    def test_does_not_return_dict(self):
        a = _make_authenticator()
        assert not isinstance(a, dict)

    def test_satisfies_bybit_authenticator_protocol(self):
        a = _make_authenticator()
        assert isinstance(a, BybitAuthenticator)

    def test_has_authenticate_method(self):
        a = _make_authenticator()
        assert callable(getattr(a, "authenticate", None))


# ---------------------------------------------------------------------------
# 8. Grafo e identidad
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_credentials_stored_by_identity(self):
        creds = _make_credentials()
        a = create_bybit_authenticator(
            credentials=creds, clock=SpyClock(), signer=SpySigner(), recv_window_ms=5_000
        )
        assert a._credentials is creds

    def test_clock_stored_by_identity(self):
        clock = SpyClock()
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        assert a._clock is clock

    def test_signer_stored_by_identity(self):
        signer = SpySigner()
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        assert a._signer is signer

    def test_recv_window_ms_stored(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=SpySigner(), recv_window_ms=7_500
        )
        assert a._recv_window_ms == 7_500

    def test_all_dependencies_stored(self):
        creds = _make_credentials()
        clock = SpyClock()
        signer = SpySigner()
        a = create_bybit_authenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5_000
        )
        assert a._credentials is creds
        assert a._clock is clock
        assert a._signer is signer
        assert a._recv_window_ms == 5_000

    def test_does_not_wrap_clock(self):
        clock = SpyClock()
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        assert type(a._clock) is SpyClock

    def test_does_not_wrap_signer(self):
        signer = SpySigner()
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        assert type(a._signer) is SpySigner


# ---------------------------------------------------------------------------
# 9. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_authenticators(self):
        creds = _make_credentials()
        clock = SpyClock()
        signer = SpySigner()
        a1 = create_bybit_authenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5_000
        )
        a2 = create_bybit_authenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5_000
        )
        assert a1 is not a2

    def test_clock_identity_preserved_across_calls(self):
        clock = SpyClock()
        a1 = create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        a2 = create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        assert a1._clock is clock
        assert a2._clock is clock

    def test_signer_identity_preserved_across_calls(self):
        signer = SpySigner()
        a1 = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        a2 = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        assert a1._signer is signer
        assert a2._signer is signer

    def test_no_global_state_between_calls(self):
        creds1 = _make_credentials("k1", "s1")
        clock1 = SpyClock(1000)
        creds2 = _make_credentials("k2", "s2")
        clock2 = SpyClock(2000)
        a1 = create_bybit_authenticator(
            credentials=creds1, clock=clock1, signer=SpySigner(), recv_window_ms=5_000
        )
        a2 = create_bybit_authenticator(
            credentials=creds2, clock=clock2, signer=SpySigner(), recv_window_ms=5_000
        )
        assert a1._credentials is creds1 and a1._clock is clock1
        assert a2._credentials is creds2 and a2._clock is clock2


# ---------------------------------------------------------------------------
# 10. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_clock_not_called_during_construction(self):
        clock = SpyClock()
        create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        assert clock.calls == []

    def test_signer_not_called_during_construction(self):
        signer = SpySigner()
        create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        assert signer.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_authenticator(
                credentials=_make_credentials(),
                clock=SpyClock(),
                signer=SpySigner(),
                recv_window_ms=5_000,
            )
        finally:
            socket.socket.connect = original
        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        a = create_bybit_authenticator(
            credentials=_make_credentials(),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        assert isinstance(a, StandardBybitAuthenticator)


# ---------------------------------------------------------------------------
# 11. Comportamiento integrado mínimo del authenticator
# ---------------------------------------------------------------------------

class TestIntegratedAuthenticatorBehavior:
    def test_authenticate_returns_bybit_authentication(self):
        a = _make_authenticator()
        result = a.authenticate(body="")
        assert isinstance(result, BybitAuthentication)

    def test_authenticate_uses_clock(self):
        clock = SpyClock(result=1_234_567_890_000)
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=clock, signer=SpySigner(), recv_window_ms=5_000
        )
        result = a.authenticate(body="")
        assert result.timestamp_ms == 1_234_567_890_000
        assert len(clock.calls) == 1

    def test_authenticate_includes_api_key(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(api_key="my_key"),
            clock=SpyClock(),
            signer=SpySigner(),
            recv_window_ms=5_000,
        )
        result = a.authenticate(body="")
        assert result.api_key == "my_key"

    def test_authenticate_includes_recv_window(self):
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=SpySigner(), recv_window_ms=9_000
        )
        result = a.authenticate(body="")
        assert result.recv_window_ms == 9_000

    def test_authenticate_includes_signature(self):
        sig_value = "abcdef1234567890" * 4
        signer = SpySigner(result=sig_value)
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        result = a.authenticate(body="")
        assert result.signature == sig_value

    def test_authenticate_calls_signer_exactly_once(self):
        signer = SpySigner()
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=signer, recv_window_ms=5_000
        )
        a.authenticate(body="somebody")
        assert len(signer.calls) == 1

    def test_authenticate_passes_secret_to_signer(self):
        signer = SpySigner()
        a = create_bybit_authenticator(
            credentials=_make_credentials(api_secret="my_secret"),
            clock=SpyClock(),
            signer=signer,
            recv_window_ms=5_000,
        )
        a.authenticate(body="")
        assert signer.calls[0]["secret"] == "my_secret"

    def test_clock_error_propagates(self):
        err = RuntimeError("clock broken")
        raising_clock = RaisingClock(error=err)
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=raising_clock, signer=SpySigner(), recv_window_ms=5_000
        )
        with pytest.raises(RuntimeError) as exc_info:
            a.authenticate(body="")
        assert exc_info.value is err

    def test_signer_error_propagates(self):
        err = ValueError("sign failed")
        raising_signer = RaisingSigner(error=err)
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=raising_signer, recv_window_ms=5_000
        )
        with pytest.raises(ValueError) as exc_info:
            a.authenticate(body="")
        assert exc_info.value is err

    def test_no_retry_after_signer_error(self):
        raising_signer = RaisingSigner(error=RuntimeError("fail"))
        a = create_bybit_authenticator(
            credentials=_make_credentials(), clock=SpyClock(), signer=raising_signer, recv_window_ms=5_000
        )
        with pytest.raises(RuntimeError):
            a.authenticate(body="")
        assert raising_signer.call_count == 1


# ---------------------------------------------------------------------------
# 12. Integración compositiva completa
# ---------------------------------------------------------------------------

class TestCompositiveIntegration:
    def _build_full_stack(self):
        spy_clock = SpyClock()
        spy_signer = SpySigner()
        creds = _make_credentials()
        spy_header_builder = SpyHeaderBuilder()
        spy_serializer = SpySerializer()

        authenticator = create_bybit_authenticator(
            credentials=creds,
            clock=spy_clock,
            signer=spy_signer,
            recv_window_ms=5_000,
        )
        request_builder = create_bybit_request_builder(
            serializer=spy_serializer,
            authenticator=authenticator,
            header_builder=spy_header_builder,
        )
        return (
            request_builder,
            authenticator,
            spy_clock,
            spy_signer,
            creds,
            spy_header_builder,
            spy_serializer,
        )

    def test_authenticator_satisfies_bybit_authenticator_protocol(self):
        _, authenticator, *_ = self._build_full_stack()
        assert isinstance(authenticator, BybitAuthenticator)

    def test_authenticator_identity_in_builder(self):
        request_builder, authenticator, *_ = self._build_full_stack()
        assert request_builder._authenticator is authenticator

    def test_clock_identity_in_authenticator(self):
        _, authenticator, spy_clock, *_ = self._build_full_stack()
        assert authenticator._clock is spy_clock

    def test_signer_identity_in_authenticator(self):
        _, authenticator, _, spy_signer, *_ = self._build_full_stack()
        assert authenticator._signer is spy_signer

    def test_credentials_identity_in_authenticator(self):
        _, authenticator, _, _, creds, *_ = self._build_full_stack()
        assert authenticator._credentials is creds

    def test_no_execution_during_full_composition(self):
        _, _, spy_clock, spy_signer, _, spy_header_builder, _ = self._build_full_stack()
        assert spy_clock.calls == []
        assert spy_signer.calls == []
        assert spy_header_builder.calls == []

    def test_request_builder_uses_authenticator_when_called(self):
        request_builder, _, spy_clock, *_ = self._build_full_stack()
        result = request_builder.build(
            url="https://api-demo.bybit.com/v5/order/create", payload={}
        )
        assert isinstance(result, HttpRequest)
        assert len(spy_clock.calls) == 1


# ---------------------------------------------------------------------------
# 13. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_raw_api_key(self):
        src = inspect.getsource(create_bybit_authenticator)
        assert "API_KEY" not in src
        assert "BYBIT_" not in src

    def test_does_not_import_request_builder(self):
        assert "BybitRequestBuilder" not in vars(_module)

    def test_does_not_import_header_builder(self):
        assert "BybitHeaderBuilder" not in vars(_module)

    def test_does_not_import_json_serializer(self):
        assert "JsonSerializer" not in vars(_module)

    def test_does_not_import_standard_serializer(self):
        assert "StandardJsonSerializer" not in vars(_module)

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_http_request_executor(self):
        assert "HttpRequestExecutor" not in vars(_module)

    def test_does_not_import_private_request_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)
