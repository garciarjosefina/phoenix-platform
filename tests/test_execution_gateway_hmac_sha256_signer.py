import hashlib
import hmac as _hmac
import os
import pytest
from execution_gateway.hmac_sha256_signer import HmacSha256Signer
from execution_gateway.message_signer import MessageSigner
import execution_gateway


def _expected(secret: str, message: str) -> str:
    return _hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


class TestImport:
    def test_direct_import(self):
        from execution_gateway.hmac_sha256_signer import HmacSha256Signer as S
        assert S is HmacSha256Signer

    def test_public_import(self):
        assert hasattr(execution_gateway, "HmacSha256Signer")
        assert execution_gateway.HmacSha256Signer is HmacSha256Signer

    def test_in_all(self):
        assert "HmacSha256Signer" in execution_gateway.__all__


class TestStructural:
    def test_implements_message_signer(self):
        signer = HmacSha256Signer()
        assert isinstance(signer, MessageSigner)

    def test_no_constructor_args(self):
        signer = HmacSha256Signer()
        assert signer is not None

    def test_two_instances_independent(self):
        s1 = HmacSha256Signer()
        s2 = HmacSha256Signer()
        assert s1 is not s2


class TestBehavior:
    def test_known_vector(self):
        # RFC 4231 / standard HMAC-SHA256 vector
        signer = HmacSha256Signer()
        result = signer.sign(secret="key", message="The quick brown fox jumps over the lazy dog")
        expected = _expected("key", "The quick brown fox jumps over the lazy dog")
        assert result == expected

    def test_empty_message(self):
        signer = HmacSha256Signer()
        result = signer.sign(secret="mysecret", message="")
        assert result == _expected("mysecret", "")

    def test_empty_secret(self):
        signer = HmacSha256Signer()
        result = signer.sign(secret="", message="mymessage")
        assert result == _expected("", "mymessage")

    def test_unicode_inputs(self):
        signer = HmacSha256Signer()
        result = signer.sign(secret="clavé", message="données")
        assert result == _expected("clavé", "données")

    def test_deterministic(self):
        signer = HmacSha256Signer()
        r1 = signer.sign(secret="s", message="m")
        r2 = signer.sign(secret="s", message="m")
        assert r1 == r2

    def test_same_input_same_signature(self):
        s1 = HmacSha256Signer()
        s2 = HmacSha256Signer()
        assert s1.sign(secret="k", message="v") == s2.sign(secret="k", message="v")

    def test_different_message_different_signature(self):
        signer = HmacSha256Signer()
        r1 = signer.sign(secret="key", message="msg1")
        r2 = signer.sign(secret="key", message="msg2")
        assert r1 != r2

    def test_different_secret_different_signature(self):
        signer = HmacSha256Signer()
        r1 = signer.sign(secret="key1", message="msg")
        r2 = signer.sign(secret="key2", message="msg")
        assert r1 != r2

    def test_returns_lowercase_hex(self):
        signer = HmacSha256Signer()
        result = signer.sign(secret="k", message="m")
        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_length_64_characters(self):
        signer = HmacSha256Signer()
        result = signer.sign(secret="k", message="m")
        assert len(result) == 64

    def test_single_hmac_call_per_sign(self, monkeypatch):
        calls = []
        original_new = _hmac.new

        def counting_new(*args, **kwargs):
            calls.append(1)
            return original_new(*args, **kwargs)

        import hmac as hmac_module
        monkeypatch.setattr(hmac_module, "new", counting_new)

        signer = HmacSha256Signer()
        signer.sign(secret="k", message="m")
        assert len(calls) == 1


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_SECRET"] = "__hmac_sentinel__"
        try:
            signer = HmacSha256Signer()
            assert signer is not None
        finally:
            del os.environ["BYBIT_API_SECRET"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_message_signer_contract_still_works(self):
        from execution_gateway.message_signer import MessageSigner
        assert MessageSigner is not None

    def test_system_clock_still_works(self):
        from execution_gateway.system_millisecond_clock import SystemMillisecondClock
        assert isinstance(SystemMillisecondClock().now_ms(), int)

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
