import inspect
import os

import pytest

import execution_gateway
from execution_gateway import create_execution_gateway as ceg
from execution_gateway.config import GatewayConfig
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway.factory import create_execution_gateway
from execution_gateway.fake_gateway import FakeExecutionGateway
from execution_gateway.gateway import ExecutionGateway


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


# ── firma pública (Core Hardening Pack A, Parte H) ─────────────────────────

def test_signature_has_only_config_parameter():
    sig = inspect.signature(create_execution_gateway)
    assert list(sig.parameters) == ["config"]


def test_no_client_parameter():
    sig = inspect.signature(create_execution_gateway)
    assert "client" not in sig.parameters


def test_rejects_client_keyword_argument():
    with pytest.raises(TypeError):
        create_execution_gateway(_dry(), client=object())


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


def test_two_calls_return_distinct_instances():
    gw1 = create_execution_gateway(_dry())
    gw2 = create_execution_gateway(_dry())
    assert gw1 is not gw2


def test_does_not_return_fake_gateway():
    gw = create_execution_gateway(_dry())
    assert not isinstance(gw, FakeExecutionGateway)


# ── modo live — sin adaptador específico ───────────────────────────────────

def test_live_raises_value_error():
    with pytest.raises(ValueError):
        create_execution_gateway(_live())


def test_live_error_message_does_not_name_any_exchange():
    with pytest.raises(ValueError) as exc_info:
        create_execution_gateway(_live())
    message = str(exc_info.value)
    assert "Bybit" not in message
    assert "Binance" not in message
    assert "OKX" not in message


def test_live_error_message_mentions_composition_root():
    with pytest.raises(ValueError, match="composition root"):
        create_execution_gateway(_live())


def test_live_does_not_return_a_gateway():
    try:
        create_execution_gateway(_live())
        assert False, "expected ValueError"
    except ValueError:
        pass


# ── pureza — sin conocimiento de ningún adaptador concreto ─────────────────

def test_factory_module_does_not_import_bybit():
    import execution_gateway.factory as module
    src = inspect.getsource(module)
    assert "Bybit" not in src


def test_factory_module_imports_no_bybit_symbol():
    import execution_gateway.factory as module
    for name in vars(module):
        assert not name.startswith("Bybit")


# ── sin efectos secundarios ────────────────────────────────────────────────

def test_no_env_read():
    os.environ["BYBIT_API_KEY"] = "__sentinel__"
    try:
        gw = create_execution_gateway(_dry())
        assert gw is not None
    finally:
        del os.environ["BYBIT_API_KEY"]
