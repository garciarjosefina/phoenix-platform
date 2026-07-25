import pytest
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway import DryRunExecutionGateway as DREG
from execution_gateway.config import GatewayConfig
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.gateway import ExecutionGateway
import execution_gateway


# ── helpers ────────────────────────────────────────────────────────────────

def _config_dry() -> GatewayConfig:
    return GatewayConfig(dry_run=True)


def _config_live() -> GatewayConfig:
    return GatewayConfig(dry_run=False)


def _request(order_id: str = "ord-1", order_type: str = "market", **kw) -> ExecutionRequest:
    defaults = dict(symbol="BTCUSDT", side="buy", quantity=0.01)
    if order_type == "limit":
        defaults["price"] = 60_000.0
    return ExecutionRequest(order_id=order_id, order_type=order_type, **{**defaults, **kw})


# ── importación pública ────────────────────────────────────────────────────

def test_import_from_module():
    assert DryRunExecutionGateway is not None


def test_import_from_package():
    assert DREG is DryRunExecutionGateway


def test_in_all():
    assert "DryRunExecutionGateway" in execution_gateway.__all__


# ── compatibilidad estructural ─────────────────────────────────────────────

def test_implements_gateway_protocol():
    gw = DryRunExecutionGateway(_config_dry())
    assert isinstance(gw, ExecutionGateway)


# ── construcción ──────────────────────────────────────────────────────────

def test_valid_construction_with_dry_run_true():
    gw = DryRunExecutionGateway(_config_dry())
    assert gw is not None


def test_rejects_dry_run_false():
    with pytest.raises(ValueError):
        DryRunExecutionGateway(_config_live())


# ── last_request inicial ───────────────────────────────────────────────────

def test_last_request_is_none_initially():
    gw = DryRunExecutionGateway(_config_dry())
    assert gw.last_request is None


# ── comportamiento de execute ──────────────────────────────────────────────

def test_saves_last_request():
    gw = DryRunExecutionGateway(_config_dry())
    req = _request()
    gw.execute(req)
    assert gw.last_request is req


def test_returns_accepted_status():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request())
    assert result.status == "accepted"


def test_preserves_order_id():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request("ord-42"))
    assert result.order_id == "ord-42"


def test_no_exchange_order_id():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request())
    assert result.exchange_order_id is None


def test_no_filled_quantity():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request())
    assert result.filled_quantity == 0.0


def test_no_average_price():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request())
    assert result.average_price is None


def test_no_error_message():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request())
    assert result.error_message is None


# ── tipos de orden ─────────────────────────────────────────────────────────

def test_works_with_market_order():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request(order_type="market"))
    assert result.status == "accepted"


def test_works_with_limit_order():
    gw = DryRunExecutionGateway(_config_dry())
    result = gw.execute(_request(order_type="limit"))
    assert result.status == "accepted"


# ── inmutabilidad de la solicitud ──────────────────────────────────────────

def test_does_not_modify_request():
    gw = DryRunExecutionGateway(_config_dry())
    req = _request("ord-1")
    gw.execute(req)
    assert req.order_id == "ord-1"
    assert req.symbol == "BTCUSDT"
    assert req.quantity == 0.01


# ── dos ejecuciones generan objetos distintos ──────────────────────────────

def test_two_executions_return_distinct_objects():
    gw = DryRunExecutionGateway(_config_dry())
    req = _request()
    r1 = gw.execute(req)
    r2 = gw.execute(req)
    assert r1 is not r2
