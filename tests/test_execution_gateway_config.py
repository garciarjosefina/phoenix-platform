import pytest
from execution_gateway.config import GatewayConfig
from execution_gateway import GatewayConfig as GatewayConfigFromInit
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway.factory import create_execution_gateway
from execution_gateway.contracts import ExecutionRequest


# ── importación ────────────────────────────────────────────────────────────

def test_import_from_module():
    assert GatewayConfig is not None


def test_import_from_package():
    assert GatewayConfigFromInit is GatewayConfig


# ── valores por defecto ────────────────────────────────────────────────────

def test_default_environment():
    assert GatewayConfig().environment == "demo"


def test_default_dry_run():
    assert GatewayConfig().dry_run is True


def test_default_timeout_seconds():
    assert GatewayConfig().timeout_seconds == 10


# ── creación válida ────────────────────────────────────────────────────────

def test_valid_demo():
    cfg = GatewayConfig(environment="demo")
    assert cfg.environment == "demo"


def test_valid_dry_run_false():
    cfg = GatewayConfig(dry_run=False)
    assert cfg.dry_run is False


def test_valid_custom_timeout():
    cfg = GatewayConfig(timeout_seconds=30)
    assert cfg.timeout_seconds == 30


# ── rechazos de entorno ────────────────────────────────────────────────────

def test_rejects_testnet():
    with pytest.raises(ValueError):
        GatewayConfig(environment="testnet")


def test_rejects_mainnet():
    with pytest.raises(ValueError):
        GatewayConfig(environment="mainnet")


def test_rejects_production():
    with pytest.raises(ValueError):
        GatewayConfig(environment="production")


def test_rejects_sandbox():
    with pytest.raises(ValueError):
        GatewayConfig(environment="sandbox")


def test_rejects_empty_environment():
    with pytest.raises(ValueError):
        GatewayConfig(environment="")


def test_rejects_demo_uppercase():
    with pytest.raises(ValueError):
        GatewayConfig(environment="DEMO")


def test_rejects_demo_titlecase():
    with pytest.raises(ValueError):
        GatewayConfig(environment="Demo")


# ── rechazos de timeout ────────────────────────────────────────────────────

def test_rejects_zero_timeout():
    with pytest.raises(ValueError):
        GatewayConfig(timeout_seconds=0)


def test_rejects_negative_timeout():
    with pytest.raises(ValueError):
        GatewayConfig(timeout_seconds=-5)


# ── inmutabilidad ──────────────────────────────────────────────────────────

def test_immutability():
    cfg = GatewayConfig()
    with pytest.raises(AttributeError):
        cfg.environment = "other"


# ── sin efectos secundarios al importar ───────────────────────────────────

def test_no_global_state():
    cfg1 = GatewayConfig()
    cfg2 = GatewayConfig()
    assert cfg1 is not cfg2
    assert cfg1 == cfg2


# ── integración: DryRunExecutionGateway ───────────────────────────────────

def test_dry_run_gateway_with_demo_config():
    cfg = GatewayConfig(environment="demo", dry_run=True)
    gw = DryRunExecutionGateway(cfg)
    req = ExecutionRequest(
        order_id="ord-1", symbol="BTCUSDT", side="buy",
        order_type="market", quantity=0.01,
    )
    result = gw.execute(req)
    assert result.status == "accepted"
    assert result.order_id == "ord-1"


# ── integración: create_execution_gateway ─────────────────────────────────

def test_factory_with_demo_dry_run():
    cfg = GatewayConfig(environment="demo", dry_run=True)
    gw = create_execution_gateway(cfg)
    assert isinstance(gw, DryRunExecutionGateway)
