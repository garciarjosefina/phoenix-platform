import os
import pytest
from execution_gateway.credentials import BybitDemoCredentials
import execution_gateway


class TestImport:
    def test_direct_import(self):
        from execution_gateway.credentials import BybitDemoCredentials as C
        assert C is BybitDemoCredentials

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitDemoCredentials")
        assert execution_gateway.BybitDemoCredentials is BybitDemoCredentials

    def test_in_all(self):
        assert "BybitDemoCredentials" in execution_gateway.__all__


class TestCreation:
    def test_valid_creation(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="secret456")
        assert creds.api_key == "key123"
        assert creds.api_secret == "secret456"

    def test_api_key_preserved_exactly(self):
        creds = BybitDemoCredentials(api_key="  Key  ", api_secret="secret456")
        assert creds.api_key == "  Key  "

    def test_api_secret_preserved_exactly(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="  Secret  ")
        assert creds.api_secret == "  Secret  "

    def test_case_preserved(self):
        creds = BybitDemoCredentials(api_key="MixedCase", api_secret="MixedSecret")
        assert creds.api_key == "MixedCase"
        assert creds.api_secret == "MixedSecret"


class TestImmutability:
    def test_frozen(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="secret456")
        with pytest.raises(Exception):
            creds.api_key = "other"

    def test_frozen_secret(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="secret456")
        with pytest.raises(Exception):
            creds.api_secret = "other"


class TestValidation:
    def test_empty_api_key(self):
        with pytest.raises(ValueError):
            BybitDemoCredentials(api_key="", api_secret="secret456")

    def test_empty_api_secret(self):
        with pytest.raises(ValueError):
            BybitDemoCredentials(api_key="key123", api_secret="")

    def test_whitespace_only_api_key(self):
        with pytest.raises(ValueError):
            BybitDemoCredentials(api_key="   ", api_secret="secret456")

    def test_whitespace_only_api_secret(self):
        with pytest.raises(ValueError):
            BybitDemoCredentials(api_key="key123", api_secret="   ")

    def test_none_api_key(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key=None, api_secret="secret456")

    def test_none_api_secret(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key="key123", api_secret=None)

    def test_int_api_key(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key=123, api_secret="secret456")

    def test_int_api_secret(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key="key123", api_secret=456)

    def test_bytes_api_key(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key=b"key123", api_secret="secret456")

    def test_bytes_api_secret(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key="key123", api_secret=b"secret456")

    def test_list_api_key(self):
        with pytest.raises(TypeError):
            BybitDemoCredentials(api_key=["key"], api_secret="secret456")


class TestSecretProtection:
    def test_secret_not_in_repr(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="supersecret")
        assert "supersecret" not in repr(creds)

    def test_secret_not_in_str(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="supersecret")
        assert "supersecret" not in str(creds)

    def test_api_key_visible_in_repr(self):
        creds = BybitDemoCredentials(api_key="key123", api_secret="supersecret")
        assert "key123" in repr(creds)


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        sentinel = "__BYBIT_SENTINEL_XYZ__"
        os.environ["BYBIT_API_KEY"] = sentinel
        os.environ["BYBIT_API_SECRET"] = sentinel
        try:
            creds = BybitDemoCredentials(api_key="key123", api_secret="secret456")
            assert creds.api_key == "key123"
            assert creds.api_secret == "secret456"
        finally:
            del os.environ["BYBIT_API_KEY"]
            del os.environ["BYBIT_API_SECRET"]


class TestExistingGatewaysUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        cfg = GatewayConfig()
        assert cfg.environment == "demo"

    def test_fake_gateway_still_works(self):
        from execution_gateway.fake_gateway import FakeExecutionGateway
        from execution_gateway.contracts import ExecutionResult
        result = ExecutionResult(order_id="ord_x", status="accepted")
        gw = FakeExecutionGateway(result=result)
        assert gw is not None

    def test_dry_run_gateway_still_works(self):
        from execution_gateway.dry_run_gateway import DryRunExecutionGateway
        from execution_gateway.config import GatewayConfig
        gw = DryRunExecutionGateway(config=GatewayConfig())
        assert gw is not None

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
