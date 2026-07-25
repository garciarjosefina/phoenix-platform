import typing
import pytest
from execution_gateway.gateway import ExecutionGateway
from execution_gateway import ExecutionGateway as EG
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway import ExecutionGateway as _check_all


# ── helpers ────────────────────────────────────────────────────────────────

def _request() -> ExecutionRequest:
    return ExecutionRequest(
        order_id="ord-1", symbol="BTCUSDT", side="buy",
        order_type="market", quantity=0.01,
    )


def _result_accepted() -> ExecutionResult:
    return ExecutionResult(order_id="ord-1", status="accepted")


class _FakeGateway:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return ExecutionResult(order_id=request.order_id, status="accepted")


class _NoExecuteGateway:
    def submit(self, request: ExecutionRequest) -> ExecutionResult:  # wrong method name
        return ExecutionResult(order_id=request.order_id, status="accepted")


# ── importación pública ────────────────────────────────────────────────────

def test_import_from_gateway_module():
    assert ExecutionGateway is not None


def test_import_from_package():
    assert EG is ExecutionGateway


def test_in_all():
    import execution_gateway
    assert "ExecutionGateway" in execution_gateway.__all__


# ── es un Protocol ─────────────────────────────────────────────────────────

def test_is_protocol():
    assert issubclass(ExecutionGateway, typing.Protocol)


def test_is_runtime_checkable():
    assert hasattr(ExecutionGateway, "__protocol_attrs__") or True
    # runtime_checkable allows isinstance checks without raising TypeError
    try:
        isinstance(object(), ExecutionGateway)
    except TypeError:
        pytest.fail("ExecutionGateway is not runtime_checkable")


# ── comprobación estructural ───────────────────────────────────────────────

def test_valid_impl_passes_isinstance():
    assert isinstance(_FakeGateway(), ExecutionGateway)


def test_missing_execute_fails_isinstance():
    assert not isinstance(_NoExecuteGateway(), ExecutionGateway)


def test_plain_object_fails_isinstance():
    assert not isinstance(object(), ExecutionGateway)


# ── ejecución de implementación falsa ─────────────────────────────────────

def test_fake_gateway_executes():
    gw = _FakeGateway()
    req = _request()
    result = gw.execute(req)
    assert isinstance(result, ExecutionResult)
    assert result.order_id == "ord-1"
    assert result.status == "accepted"


def test_fake_gateway_passes_request_through():
    gw = _FakeGateway()
    req = ExecutionRequest(
        order_id="ord-99", symbol="ETHUSDT", side="sell",
        order_type="market", quantity=1.0,
    )
    result = gw.execute(req)
    assert result.order_id == "ord-99"


# ── sin dependencias externas ──────────────────────────────────────────────

def test_no_external_imports():
    import execution_gateway.gateway as gw_module
    import sys
    stdlib_and_local = {"typing", "execution_gateway"}
    for name in vars(gw_module):
        obj = getattr(gw_module, name)
        mod = getattr(obj, "__module__", "") or ""
        top = mod.split(".")[0]
        if top and top not in stdlib_and_local and not name.startswith("_"):
            pytest.fail(f"Unexpected external import in gateway.py: {name} from {mod}")
