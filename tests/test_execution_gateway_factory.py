import os
import pytest
from execution_gateway.factory import create_execution_gateway
from execution_gateway import create_execution_gateway as ceg
from execution_gateway.config import GatewayConfig
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.gateway import ExecutionGateway
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.fake_gateway import FakeExecutionGateway
import execution_gateway


# ── helpers ────────────────────────────────────────────────────────────────

def _dry() -> GatewayConfig:
    return GatewayConfig(dry_run=True)


def _live() -> GatewayConfig:
    return GatewayConfig(dry_run=False)


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        order_id="ord-1", symbol="BTCUSDT", side="buy",
        order_type="market", quantity=0.01,
    )


class _ValidClient:
    def __init__(self):
        self.call_count = 0

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.call_count += 1
        return BybitCreateOrderResult(order_id="mock-order-id", order_link_id="mock-link-id")


class _NoPlaceOrder:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...


# ── importación pública ────────────────────────────────────────────────────

def test_import_from_factory_module():
    assert create_execution_gateway is not None


def test_import_from_package():
    assert ceg is create_execution_gateway


def test_in_all():
    assert "create_execution_gateway" in execution_gateway.__all__


# ── modo dry_run ───────────────────────────────────────────────────────────

def test_returns_dry_run_gateway():
    gw = create_execution_gateway(_dry())
    assert isinstance(gw, DryRunExecutionGateway)


def test_result_implements_gateway_protocol():
    gw = create_execution_gateway(_dry())
    assert isinstance(gw, ExecutionGateway)


def test_gateway_executes_request():
    gw = create_execution_gateway(_dry())
    result = gw.execute(_request())
    assert isinstance(result, ExecutionResult)
    assert result.status == "accepted"
    assert result.order_id == "ord-1"


def test_dry_run_without_client():
    gw = create_execution_gateway(_dry())
    assert isinstance(gw, DryRunExecutionGateway)


def test_dry_run_ignores_valid_client():
    gw = create_execution_gateway(_dry(), client=_ValidClient())
    assert isinstance(gw, DryRunExecutionGateway)


def test_dry_run_ignores_incompatible_object():
    gw = create_execution_gateway(_dry(), client=_NoPlaceOrder())
    assert isinstance(gw, DryRunExecutionGateway)


# ── modo live — BybitExecutionGateway ─────────────────────────────────────

def test_live_with_valid_client_returns_bybit_gateway():
    gw = create_execution_gateway(_live(), client=_ValidClient())
    assert isinstance(gw, BybitExecutionGateway)


def test_live_gateway_implements_execution_gateway():
    gw = create_execution_gateway(_live(), client=_ValidClient())
    assert isinstance(gw, ExecutionGateway)


def test_live_gateway_delegates_to_client():
    client = _ValidClient()
    gw = create_execution_gateway(_live(), client=client)
    gw.execute(_request())
    assert client.call_count == 1


def test_factory_does_not_call_place_order():
    client = _ValidClient()
    create_execution_gateway(_live(), client=client)
    assert client.call_count == 0


def test_live_without_client_raises_value_error():
    with pytest.raises(ValueError):
        create_execution_gateway(_live())


def test_live_without_client_error_message():
    with pytest.raises(ValueError, match="BybitDemoClient"):
        create_execution_gateway(_live())


def test_live_with_incompatible_client_raises_type_error():
    with pytest.raises(TypeError):
        create_execution_gateway(_live(), client=_NoPlaceOrder())


def test_no_explicit_inheritance_required():
    class AnotherClient:
        def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
            return BybitCreateOrderResult(order_id="mock-order-id", order_link_id="mock-link-id")

    gw = create_execution_gateway(_live(), client=AnotherClient())
    assert isinstance(gw, BybitExecutionGateway)


# ── instancias distintas ───────────────────────────────────────────────────

def test_two_calls_return_distinct_instances():
    gw1 = create_execution_gateway(_dry())
    gw2 = create_execution_gateway(_dry())
    assert gw1 is not gw2


# ── no devuelve FakeExecutionGateway ──────────────────────────────────────

def test_does_not_return_fake_gateway():
    gw = create_execution_gateway(_dry())
    assert not isinstance(gw, FakeExecutionGateway)


# ── sin efectos secundarios ────────────────────────────────────────────────

def test_no_env_read():
    os.environ["BYBIT_API_KEY"] = "__sentinel__"
    try:
        gw = create_execution_gateway(_dry())
        assert gw is not None
    finally:
        del os.environ["BYBIT_API_KEY"]
