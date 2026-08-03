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


# ── validación estricta de tipos (Core Hardening Pack A, Parte G) ─────────

def test_rejects_non_str_environment():
    with pytest.raises(TypeError, match="environment must be str"):
        GatewayConfig(environment=123)


def test_rejects_none_environment():
    with pytest.raises(TypeError, match="environment must be str"):
        GatewayConfig(environment=None)


def test_rejects_whitespace_only_environment():
    with pytest.raises(ValueError, match="environment must not be empty or whitespace-only"):
        GatewayConfig(environment="   ")


def test_environment_not_stripped():
    with pytest.raises(ValueError):
        GatewayConfig(environment=" demo ")


def test_rejects_string_dry_run():
    with pytest.raises(TypeError, match="dry_run must be bool"):
        GatewayConfig(dry_run="false")


def test_rejects_string_true_dry_run():
    with pytest.raises(TypeError, match="dry_run must be bool"):
        GatewayConfig(dry_run="true")


def test_rejects_int_one_dry_run():
    with pytest.raises(TypeError, match="dry_run must be bool"):
        GatewayConfig(dry_run=1)


def test_rejects_int_zero_dry_run():
    with pytest.raises(TypeError, match="dry_run must be bool"):
        GatewayConfig(dry_run=0)


def test_rejects_none_dry_run():
    with pytest.raises(TypeError, match="dry_run must be bool"):
        GatewayConfig(dry_run=None)


def test_accepts_bool_true_dry_run():
    assert GatewayConfig(dry_run=True).dry_run is True


def test_accepts_bool_false_dry_run():
    assert GatewayConfig(dry_run=False).dry_run is False


def test_rejects_bool_timeout_seconds():
    with pytest.raises(TypeError, match="timeout_seconds must be int"):
        GatewayConfig(timeout_seconds=True)


def test_rejects_float_timeout_seconds():
    with pytest.raises(TypeError, match="timeout_seconds must be int"):
        GatewayConfig(timeout_seconds=1.5)


def test_rejects_string_timeout_seconds():
    with pytest.raises(TypeError, match="timeout_seconds must be int"):
        GatewayConfig(timeout_seconds="10")


def test_rejects_none_timeout_seconds():
    with pytest.raises(TypeError, match="timeout_seconds must be int"):
        GatewayConfig(timeout_seconds=None)


def test_accepts_valid_int_timeout_seconds():
    assert GatewayConfig(timeout_seconds=30).timeout_seconds == 30


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
