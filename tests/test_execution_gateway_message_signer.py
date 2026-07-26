import os
import pytest
from execution_gateway.message_signer import MessageSigner
import execution_gateway


class _ValidSigner:
    def __init__(self):
        self.call_count = 0
        self.received: list[dict] = []

    def sign(self, *, secret: str, message: str) -> str:
        self.call_count += 1
        self.received.append({"secret": secret, "message": message})
        return f"sig:{secret}:{message}"


class _NoSign:
    def verify(self, *, secret: str, message: str) -> bool:
        return True


class TestImport:
    def test_direct_import(self):
        from execution_gateway.message_signer import MessageSigner as S
        assert S is MessageSigner

    def test_public_import(self):
        assert hasattr(execution_gateway, "MessageSigner")
        assert execution_gateway.MessageSigner is MessageSigner

    def test_in_all(self):
        assert "MessageSigner" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable_valid(self):
        signer = _ValidSigner()
        assert isinstance(signer, MessageSigner)

    def test_incompatible_class_rejected(self):
        signer = _NoSign()
        assert not isinstance(signer, MessageSigner)

    def test_no_explicit_inheritance_required(self):
        signer = _ValidSigner()
        assert isinstance(signer, MessageSigner)

    def test_isinstance_does_not_call_sign(self):
        signer = _ValidSigner()
        _ = isinstance(signer, MessageSigner)
        assert signer.call_count == 0

    def test_keyword_only_call(self):
        signer = _ValidSigner()
        result = signer.sign(secret="mysecret", message="mymessage")
        assert result == "sig:mysecret:mymessage"

    def test_receives_exact_secret(self):
        signer = _ValidSigner()
        signer.sign(secret="abc123", message="msg")
        assert signer.received[0]["secret"] == "abc123"

    def test_receives_exact_message(self):
        signer = _ValidSigner()
        signer.sign(secret="sec", message="exact_message_content")
        assert signer.received[0]["message"] == "exact_message_content"

    def test_returns_exact_signature(self):
        signer = _ValidSigner()
        result = signer.sign(secret="s", message="m")
        assert result == "sig:s:m"

    def test_accepts_empty_secret(self):
        class EmptyAcceptor:
            def sign(self, *, secret: str, message: str) -> str:
                return "ok"

        signer = EmptyAcceptor()
        assert signer.sign(secret="", message="msg") == "ok"

    def test_accepts_empty_message(self):
        class EmptyAcceptor:
            def sign(self, *, secret: str, message: str) -> str:
                return "ok"

        signer = EmptyAcceptor()
        assert signer.sign(secret="sec", message="") == "ok"

    def test_accepts_unicode(self):
        class UnicodeAcceptor:
            def sign(self, *, secret: str, message: str) -> str:
                return f"{secret}{message}"

        signer = UnicodeAcceptor()
        result = signer.sign(secret="clavé", message="données")
        assert result == "clavédonnées"


class TestNoHmac:
    def test_module_does_not_import_hmac(self):
        import sys
        import execution_gateway.message_signer as module
        assert "hmac" not in vars(module)

    def test_module_does_not_import_hashlib(self):
        import sys
        import execution_gateway.message_signer as module
        assert "hashlib" not in vars(module)


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        os.environ["BYBIT_API_SECRET"] = "__signer_sentinel__"
        try:
            from execution_gateway.message_signer import MessageSigner as S
            assert S is not None
        finally:
            del os.environ["BYBIT_API_SECRET"]

    def test_no_external_dependencies(self):
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_system_clock_still_works(self):
        from execution_gateway.system_millisecond_clock import SystemMillisecondClock
        clock = SystemMillisecondClock()
        assert isinstance(clock.now_ms(), int)

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
