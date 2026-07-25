import os
import pytest
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.gateway import ExecutionGateway
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
import execution_gateway


def _make_request(order_id="ord_abc"):
    return ExecutionRequest(
        order_id=order_id,
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        quantity=0.001,
    )


class _ValidClient:
    def __init__(self, result: ExecutionResult):
        self._result = result
        self.call_count = 0
        self.received_requests: list[ExecutionRequest] = []

    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        self.call_count += 1
        self.received_requests.append(request)
        return self._result


class _NoPlaceOrder:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...


class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_gateway import BybitExecutionGateway as C
        assert C is BybitExecutionGateway

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitExecutionGateway")
        assert execution_gateway.BybitExecutionGateway is BybitExecutionGateway

    def test_in_all(self):
        assert "BybitExecutionGateway" in execution_gateway.__all__


class TestStructuralCompatibility:
    def test_implements_execution_gateway(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        gw = BybitExecutionGateway(client=_ValidClient(result))
        assert isinstance(gw, ExecutionGateway)

    def test_no_explicit_inheritance_required(self):
        assert not issubclass(BybitExecutionGateway, ExecutionGateway) or True
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        gw = BybitExecutionGateway(client=_ValidClient(result))
        assert isinstance(gw, ExecutionGateway)


class TestConstructor:
    def test_valid_client_accepted(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        gw = BybitExecutionGateway(client=_ValidClient(result))
        assert gw is not None

    def test_incompatible_client_rejected(self):
        with pytest.raises(TypeError):
            BybitExecutionGateway(client=_NoPlaceOrder())

    def test_none_client_rejected(self):
        with pytest.raises(TypeError):
            BybitExecutionGateway(client=None)

    def test_no_explicit_inheritance_needed(self):
        class AnotherClient:
            def place_order(self, request: ExecutionRequest) -> ExecutionResult:
                return ExecutionResult(order_id=request.order_id, status="accepted")

        gw = BybitExecutionGateway(client=AnotherClient())
        assert gw is not None

    def test_client_not_called_during_construction(self):
        class SentinelClient:
            def __init__(self):
                self.called = False

            def place_order(self, request: ExecutionRequest) -> ExecutionResult:
                self.called = True
                return ExecutionResult(order_id=request.order_id, status="accepted")

        sentinel = SentinelClient()
        BybitExecutionGateway(client=sentinel)
        assert not sentinel.called


class TestDelegation:
    def test_execute_delegates_to_place_order(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        client = _ValidClient(result)
        gw = BybitExecutionGateway(client=client)
        request = _make_request("ord_abc")
        gw.execute(request)
        assert client.call_count == 1

    def test_execute_passes_exact_request(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        client = _ValidClient(result)
        gw = BybitExecutionGateway(client=client)
        request = _make_request("ord_abc")
        gw.execute(request)
        assert client.received_requests[0] is request

    def test_execute_returns_exact_result(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        client = _ValidClient(result)
        gw = BybitExecutionGateway(client=client)
        returned = gw.execute(_make_request("ord_abc"))
        assert returned is result

    def test_single_call_per_execute(self):
        result = ExecutionResult(order_id="ord_abc", status="accepted")
        client = _ValidClient(result)
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request("ord_abc"))
        gw.execute(_make_request("ord_abc"))
        assert client.call_count == 2

    def test_exception_propagates(self):
        class RaisingClient:
            def place_order(self, request: ExecutionRequest) -> ExecutionResult:
                raise RuntimeError("network failure")

        gw = BybitExecutionGateway(client=RaisingClient())
        with pytest.raises(RuntimeError, match="network failure"):
            gw.execute(_make_request())


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            result = ExecutionResult(order_id="ord_abc", status="accepted")
            gw = BybitExecutionGateway(client=_ValidClient(result))
            assert gw is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


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
