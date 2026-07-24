import pytest
from execution_gateway.config import GatewayConfig
from execution_gateway import GatewayConfig as GatewayConfigFromInit


# --- importación ---

def test_import_from_module():
    assert GatewayConfig is not None


def test_import_from_package():
    assert GatewayConfigFromInit is GatewayConfig


# --- valores por defecto ---

def test_default_environment():
    assert GatewayConfig().environment == "testnet"


def test_default_dry_run():
    assert GatewayConfig().dry_run is True


def test_default_timeout_seconds():
    assert GatewayConfig().timeout_seconds == 10


# --- creación con valores válidos ---

def test_valid_testnet():
    cfg = GatewayConfig(environment="testnet")
    assert cfg.environment == "testnet"


def test_valid_mainnet():
    cfg = GatewayConfig(environment="mainnet")
    assert cfg.environment == "mainnet"


def test_valid_dry_run_false():
    cfg = GatewayConfig(dry_run=False)
    assert cfg.dry_run is False


def test_valid_custom_timeout():
    cfg = GatewayConfig(timeout_seconds=30)
    assert cfg.timeout_seconds == 30


# --- rechazos ---

def test_rejects_invalid_environment():
    with pytest.raises(ValueError):
        GatewayConfig(environment="production")


def test_rejects_empty_environment():
    with pytest.raises(ValueError):
        GatewayConfig(environment="")


def test_rejects_zero_timeout():
    with pytest.raises(ValueError):
        GatewayConfig(timeout_seconds=0)


def test_rejects_negative_timeout():
    with pytest.raises(ValueError):
        GatewayConfig(timeout_seconds=-5)


# --- inmutabilidad ---

def test_immutability():
    cfg = GatewayConfig()
    with pytest.raises(AttributeError):
        cfg.environment = "mainnet"


# --- sin efectos secundarios al importar ---

def test_no_global_state():
    cfg1 = GatewayConfig()
    cfg2 = GatewayConfig()
    assert cfg1 is not cfg2
    assert cfg1 == cfg2
