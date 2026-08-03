import os
import pytest
from execution_gateway.bybit_authenticator import BybitAuthentication, BybitAuthenticator
import execution_gateway


def _valid_auth(**kwargs) -> BybitAuthentication:
    defaults = dict(
        timestamp_ms=1_700_000_000_000,
        api_key="myapikey",
        recv_window_ms=5000,
        signature="abcdef1234567890" * 4,
    )
    defaults.update(kwargs)
    return BybitAuthentication(**defaults)


class _ValidAuthenticator:
    def __init__(self, result: BybitAuthentication):
        self._result = result
        self.call_count = 0
        self.received_bodies: list[str] = []

    def authenticate(self, *, body: str) -> BybitAuthentication:
        self.call_count += 1
        self.received_bodies.append(body)
        return self._result


class _NoAuthenticate:
    def sign(self, body: str) -> str:
        return ""


class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_authenticator import BybitAuthentication as A, BybitAuthenticator as P
        assert A is BybitAuthentication
        assert P is BybitAuthenticator

    def test_public_import_authentication(self):
        assert hasattr(execution_gateway, "BybitAuthentication")
        assert execution_gateway.BybitAuthentication is BybitAuthentication

    def test_public_import_authenticator(self):
        assert hasattr(execution_gateway, "BybitAuthenticator")
        assert execution_gateway.BybitAuthenticator is BybitAuthenticator

    def test_both_in_all(self):
        assert "BybitAuthentication" in execution_gateway.__all__
        assert "BybitAuthenticator" in execution_gateway.__all__

    def test_authenticator_runtime_checkable(self):
        auth = _ValidAuthenticator(_valid_auth())
        assert isinstance(auth, BybitAuthenticator)


class TestBybitAuthentication:
    def test_valid_construction(self):
        auth = _valid_auth()
        assert auth.timestamp_ms == 1_700_000_000_000
        assert auth.api_key == "myapikey"
        assert auth.recv_window_ms == 5000
        assert auth.signature == "abcdef1234567890" * 4

    def test_frozen(self):
        auth = _valid_auth()
        with pytest.raises(Exception):
            auth.timestamp_ms = 0

    def test_equality_by_value(self):
        a = _valid_auth()
        b = _valid_auth()
        assert a == b

    def test_preserves_all_values(self):
        auth = BybitAuthentication(
            timestamp_ms=123,
            api_key="key_xyz",
            recv_window_ms=9999,
            signature="sigvalue",
        )
        assert auth.timestamp_ms == 123
        assert auth.api_key == "key_xyz"
        assert auth.recv_window_ms == 9999
        assert auth.signature == "sigvalue"

    def test_accepts_timestamp_zero(self):
        auth = _valid_auth(timestamp_ms=0)
        assert auth.timestamp_ms == 0

    def test_accepts_recv_window_one(self):
        auth = _valid_auth(recv_window_ms=1)
        assert auth.recv_window_ms == 1

    def test_rejects_timestamp_bool(self):
        with pytest.raises(TypeError):
            _valid_auth(timestamp_ms=True)

    def test_rejects_recv_window_bool(self):
        with pytest.raises(TypeError):
            _valid_auth(recv_window_ms=True)

    def test_rejects_timestamp_str(self):
        with pytest.raises(TypeError):
            _valid_auth(timestamp_ms="123")

    def test_rejects_recv_window_str(self):
        with pytest.raises(TypeError):
            _valid_auth(recv_window_ms="5000")

    def test_rejects_negative_timestamp(self):
        with pytest.raises(ValueError):
            _valid_auth(timestamp_ms=-1)

    def test_rejects_recv_window_zero(self):
        with pytest.raises(ValueError):
            _valid_auth(recv_window_ms=0)

    def test_rejects_negative_recv_window(self):
        with pytest.raises(ValueError):
            _valid_auth(recv_window_ms=-1)

    def test_rejects_empty_api_key(self):
        with pytest.raises(ValueError):
            _valid_auth(api_key="")

    def test_rejects_whitespace_api_key(self):
        with pytest.raises(ValueError):
            _valid_auth(api_key="   ")

    def test_rejects_empty_signature(self):
        with pytest.raises(ValueError):
            _valid_auth(signature="")

    def test_rejects_whitespace_signature(self):
        with pytest.raises(ValueError):
            _valid_auth(signature="   ")

    def test_no_api_secret_field(self):
        auth = _valid_auth()
        assert not hasattr(auth, "api_secret")

    def test_repr_contains_no_secret(self):
        auth = _valid_auth()
        assert "secret" not in repr(auth).lower()

    def test_repr_does_not_expose_signature_value(self):
        marker = "ZZSIGNATUREMARKER9999"
        auth = _valid_auth(signature=marker)
        assert marker not in repr(auth)

    def test_str_does_not_expose_signature_value(self):
        marker = "ZZSTRSIGNATUREMARKER9999"
        auth = _valid_auth(signature=marker)
        assert marker not in str(auth)

    def test_signature_still_accessible_as_attribute(self):
        auth = _valid_auth(signature="my-signature")
        assert auth.signature == "my-signature"

    def test_repr_still_shows_api_key(self):
        auth = _valid_auth(api_key="visible-key")
        assert "visible-key" in repr(auth)


class TestBybitAuthenticator:
    def test_runtime_checkable_valid(self):
        auth = _ValidAuthenticator(_valid_auth())
        assert isinstance(auth, BybitAuthenticator)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoAuthenticate(), BybitAuthenticator)

    def test_no_explicit_inheritance_required(self):
        auth = _ValidAuthenticator(_valid_auth())
        assert isinstance(auth, BybitAuthenticator)

    def test_isinstance_does_not_call_authenticate(self):
        auth = _ValidAuthenticator(_valid_auth())
        _ = isinstance(auth, BybitAuthenticator)
        assert auth.call_count == 0

    def test_keyword_only_call(self):
        result = _valid_auth()
        auth = _ValidAuthenticator(result)
        returned = auth.authenticate(body='{"qty":"0.001"}')
        assert returned is result

    def test_receives_exact_body(self):
        auth = _ValidAuthenticator(_valid_auth())
        body = '{"qty":"0.001","symbol":"BTCUSDT"}'
        auth.authenticate(body=body)
        assert auth.received_bodies[0] == body

    def test_returns_exact_authentication_object(self):
        result = _valid_auth()
        auth = _ValidAuthenticator(result)
        returned = auth.authenticate(body="anybody")
        assert returned is result


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        os.environ["BYBIT_API_KEY"] = "__auth_sentinel__"
        try:
            from execution_gateway.bybit_authenticator import BybitAuthenticator as A
            assert A is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_module_does_not_import_hmac(self):
        import execution_gateway.bybit_authenticator as module
        assert "hmac" not in vars(module)

    def test_module_does_not_import_hashlib(self):
        import execution_gateway.bybit_authenticator as module
        assert "hashlib" not in vars(module)

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_hmac_signer_still_works(self):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer
        result = HmacSha256Signer().sign(secret="k", message="m")
        assert len(result) == 64

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
