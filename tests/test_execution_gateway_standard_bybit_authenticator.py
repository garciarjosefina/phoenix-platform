import os
import pytest
from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator
from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
from execution_gateway.credentials import BybitDemoCredentials
from execution_gateway.millisecond_clock import MillisecondClock
from execution_gateway.message_signer import MessageSigner
import execution_gateway


# ── local test doubles ─────────────────────────────────────────────────────

class _FixedClock:
    def __init__(self, value: int = 1_700_000_000_000):
        self._value = value
        self.call_count = 0

    def now_ms(self) -> int:
        self.call_count += 1
        return self._value


class _CapturingSigner:
    def __init__(self, signature: str = "a" * 64):
        self._signature = signature
        self.call_count = 0
        self.received: list[dict] = []

    def sign(self, *, secret: str, message: str) -> str:
        self.call_count += 1
        self.received.append({"secret": secret, "message": message})
        return self._signature


class _NoClock:
    def tick(self) -> int:
        return 0


class _NoSigner:
    def compute(self, *, secret: str, message: str) -> str:
        return ""


def _creds(key="mykey", secret="mysecret") -> BybitDemoCredentials:
    return BybitDemoCredentials(api_key=key, api_secret=secret)


def _make(**kwargs) -> StandardBybitAuthenticator:
    defaults = dict(
        credentials=_creds(),
        clock=_FixedClock(),
        signer=_CapturingSigner(),
        recv_window_ms=5000,
    )
    defaults.update(kwargs)
    return StandardBybitAuthenticator(**defaults)


# ── import & contract ──────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.standard_bybit_authenticator import StandardBybitAuthenticator as S
        assert S is StandardBybitAuthenticator

    def test_public_import(self):
        assert hasattr(execution_gateway, "StandardBybitAuthenticator")
        assert execution_gateway.StandardBybitAuthenticator is StandardBybitAuthenticator

    def test_in_all(self):
        assert "StandardBybitAuthenticator" in execution_gateway.__all__

    def test_implements_bybit_authenticator(self):
        auth = _make()
        assert isinstance(auth, BybitAuthenticator)

    def test_no_explicit_inheritance_required(self):
        class AltClock:
            def now_ms(self) -> int:
                return 1

        class AltSigner:
            def sign(self, *, secret: str, message: str) -> str:
                return "x" * 64

        auth = StandardBybitAuthenticator(
            credentials=_creds(),
            clock=AltClock(),
            signer=AltSigner(),
            recv_window_ms=1000,
        )
        assert isinstance(auth, BybitAuthenticator)


# ── constructor ────────────────────────────────────────────────────────────

class TestConstructor:
    def test_valid_construction(self):
        auth = _make()
        assert auth is not None

    def test_rejects_invalid_credentials(self):
        with pytest.raises(TypeError):
            _make(credentials="not_creds")

    def test_rejects_incompatible_clock(self):
        with pytest.raises(TypeError):
            _make(clock=_NoClock())

    def test_rejects_incompatible_signer(self):
        with pytest.raises(TypeError):
            _make(signer=_NoSigner())

    def test_rejects_recv_window_bool(self):
        with pytest.raises(TypeError):
            _make(recv_window_ms=True)

    def test_rejects_recv_window_str(self):
        with pytest.raises(TypeError):
            _make(recv_window_ms="5000")

    def test_rejects_recv_window_zero(self):
        with pytest.raises(ValueError):
            _make(recv_window_ms=0)

    def test_rejects_recv_window_negative(self):
        with pytest.raises(ValueError):
            _make(recv_window_ms=-1)

    def test_clock_not_called_during_construction(self):
        clock = _FixedClock()
        _make(clock=clock)
        assert clock.call_count == 0

    def test_signer_not_called_during_construction(self):
        signer = _CapturingSigner()
        _make(signer=signer)
        assert signer.call_count == 0

    def test_no_env_read(self):
        os.environ["BYBIT_API_SECRET"] = "__auth_impl_sentinel__"
        try:
            auth = _make()
            assert auth is not None
        finally:
            del os.environ["BYBIT_API_SECRET"]


# ── authenticate ───────────────────────────────────────────────────────────

class TestAuthenticate:
    def test_body_keyword_only(self):
        auth = _make()
        result = auth.authenticate(body="anybody")
        assert isinstance(result, BybitAuthentication)

    def test_rejects_non_str_body(self):
        auth = _make()
        with pytest.raises(TypeError):
            auth.authenticate(body=123)

    def test_accepts_empty_body(self):
        auth = _make()
        result = auth.authenticate(body="")
        assert isinstance(result, BybitAuthentication)

    def test_clock_called_once(self):
        clock = _FixedClock()
        auth = _make(clock=clock)
        auth.authenticate(body="")
        assert clock.call_count == 1

    def test_signer_called_once(self):
        signer = _CapturingSigner()
        auth = _make(signer=signer)
        auth.authenticate(body="")
        assert signer.call_count == 1

    def test_secret_delivered_to_signer(self):
        signer = _CapturingSigner()
        auth = _make(credentials=_creds(secret="topsecret"), signer=signer)
        auth.authenticate(body="")
        assert signer.received[0]["secret"] == "topsecret"

    def test_message_order_timestamp_key_window_body(self):
        clock = _FixedClock(1_700_000_000_000)
        signer = _CapturingSigner()
        creds = _creds(key="MYKEY")
        auth = StandardBybitAuthenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=5000
        )
        auth.authenticate(body='{"qty":"0.001"}')
        expected = "1700000000000" + "MYKEY" + "5000" + '{"qty":"0.001"}'
        assert signer.received[0]["message"] == expected

    def test_message_no_separators(self):
        clock = _FixedClock(100)
        signer = _CapturingSigner()
        creds = _creds(key="K")
        auth = StandardBybitAuthenticator(
            credentials=creds, clock=clock, signer=signer, recv_window_ms=1
        )
        auth.authenticate(body="B")
        assert signer.received[0]["message"] == "100K1B"

    def test_body_preserved_exactly(self):
        signer = _CapturingSigner()
        auth = _make(signer=signer)
        body = '{"symbol":"BTCUSDT","qty":"0.001"}'
        auth.authenticate(body=body)
        assert signer.received[0]["message"].endswith(body)

    def test_body_unicode(self):
        signer = _CapturingSigner()
        auth = _make(clock=_FixedClock(1), signer=signer, recv_window_ms=1)
        auth.authenticate(body="données")
        assert signer.received[0]["message"].endswith("données")

    def test_result_timestamp_from_clock(self):
        clock = _FixedClock(9_999_999)
        auth = _make(clock=clock)
        result = auth.authenticate(body="")
        assert result.timestamp_ms == 9_999_999

    def test_result_api_key_from_credentials(self):
        auth = _make(credentials=_creds(key="EXACT_KEY"))
        result = auth.authenticate(body="")
        assert result.api_key == "EXACT_KEY"

    def test_result_recv_window_from_config(self):
        auth = _make(recv_window_ms=12345)
        result = auth.authenticate(body="")
        assert result.recv_window_ms == 12345

    def test_result_signature_from_signer(self):
        sig = "b" * 64
        auth = _make(signer=_CapturingSigner(sig))
        result = auth.authenticate(body="")
        assert result.signature == sig

    def test_result_is_bybit_authentication(self):
        auth = _make()
        result = auth.authenticate(body="")
        assert isinstance(result, BybitAuthentication)

    def test_clock_called_again_on_second_call(self):
        clock = _FixedClock()
        auth = _make(clock=clock)
        auth.authenticate(body="")
        auth.authenticate(body="")
        assert clock.call_count == 2

    def test_no_stored_last_result(self):
        auth = _make(clock=_FixedClock())
        auth.authenticate(body="")
        assert not hasattr(auth, "last_result")
        assert not hasattr(auth, "last_message")
        assert not hasattr(auth, "last_signature")

    def test_exception_from_clock_propagates(self):
        class FailingClock:
            def now_ms(self) -> int:
                raise RuntimeError("clock error")

        auth = _make(clock=FailingClock())
        with pytest.raises(RuntimeError, match="clock error"):
            auth.authenticate(body="")

    def test_exception_from_signer_propagates(self):
        class FailingSigner:
            def sign(self, *, secret: str, message: str) -> str:
                raise RuntimeError("signer error")

        auth = _make(signer=FailingSigner())
        with pytest.raises(RuntimeError, match="signer error"):
            auth.authenticate(body="")


# ── security ───────────────────────────────────────────────────────────────

class TestSecurity:
    def test_secret_not_in_result(self):
        auth = _make(credentials=_creds(secret="supersecret"))
        result = auth.authenticate(body="")
        assert not hasattr(result, "api_secret")

    def test_secret_not_in_repr(self):
        auth = _make(credentials=_creds(secret="supersecret"))
        assert "supersecret" not in repr(auth)


# ── suite unaffected ───────────────────────────────────────────────────────

class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_hmac_signer_still_works(self):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        assert len(HmacSha256Signer().sign(secret="k", message="m")) == 64

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
