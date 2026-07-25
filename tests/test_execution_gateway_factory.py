import pytest
from execution_gateway.factory import create_execution_gateway
from execution_gateway import create_execution_gateway as ceg
from execution_gateway.config import GatewayConfig
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.gateway import ExecutionGateway
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
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


# ── modo live — rechazo ────────────────────────────────────────────────────

def test_rejects_live_mode():
    with pytest.raises(NotImplementedError):
        create_execution_gateway(_live())


def test_live_error_message_is_clear():
    with pytest.raises(NotImplementedError, match="not yet implemented"):
        create_execution_gateway(_live())


# ── instancias distintas ───────────────────────────────────────────────────

def test_two_calls_return_distinct_instances():
    gw1 = create_execution_gateway(_dry())
    gw2 = create_execution_gateway(_dry())
    assert gw1 is not gw2


# ── no devuelve FakeExecutionGateway ──────────────────────────────────────

def test_does_not_return_fake_gateway():
    gw = create_execution_gateway(_dry())
    assert not isinstance(gw, FakeExecutionGateway)
