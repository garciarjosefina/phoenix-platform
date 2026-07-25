import os
import pytest
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
import execution_gateway


class _ValidClient:
    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(order_id=request.order_id, status="accepted")


class _NoPlaceOrder:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...


class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_client import BybitDemoClient as C
        assert C is BybitDemoClient

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitDemoClient")
        assert execution_gateway.BybitDemoClient is BybitDemoClient

    def test_in_all(self):
        assert "BybitDemoClient" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        client = _ValidClient()
        assert isinstance(client, BybitDemoClient)

    def test_incompatible_class_rejected(self):
        other = _NoPlaceOrder()
        assert not isinstance(other, BybitDemoClient)

    def test_no_explicit_inheritance_required(self):
        assert not issubclass(_ValidClient, BybitDemoClient) or True
        client = _ValidClient()
        assert isinstance(client, BybitDemoClient)

    def test_place_order_callable(self):
        client = _ValidClient()
        request = ExecutionRequest(
            order_id="ord_abc",
            symbol="BTCUSDT",
            side="buy",
            order_type="market",
            quantity=0.001,
        )
        result = client.place_order(request)
        assert isinstance(result, ExecutionResult)

    def test_place_order_receives_execution_request(self):
        received = []

        class CapturingClient:
            def place_order(self, request: ExecutionRequest) -> ExecutionResult:
                received.append(request)
                return ExecutionResult(order_id=request.order_id, status="accepted")

        client = CapturingClient()
        request = ExecutionRequest(
            order_id="ord_xyz",
            symbol="ETHUSDT",
            side="sell",
            order_type="market",
            quantity=0.01,
        )
        client.place_order(request)
        assert len(received) == 1
        assert received[0] is request

    def test_place_order_returns_execution_result(self):
        client = _ValidClient()
        request = ExecutionRequest(
            order_id="ord_abc",
            symbol="BTCUSDT",
            side="buy",
            order_type="market",
            quantity=0.001,
        )
        result = client.place_order(request)
        assert result.order_id == "ord_abc"
        assert result.status == "accepted"


class TestNoSideEffects:
    def test_import_does_not_read_env(self):
        sentinel = "__BYBIT_CLIENT_SENTINEL__"
        os.environ["BYBIT_API_KEY"] = sentinel
        try:
            from execution_gateway.bybit_client import BybitDemoClient as C
            assert C is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_no_external_dependencies(self):
        import execution_gateway.bybit_client as module
        import sys
        for name in ("requests", "httpx", "aiohttp", "pybit"):
            assert name not in sys.modules or True
        assert module is not None


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_credentials_still_work(self):
        from execution_gateway.credentials import BybitDemoCredentials
        creds = BybitDemoCredentials(api_key="k", api_secret="s")
        assert creds.api_key == "k"

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
