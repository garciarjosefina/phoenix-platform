import pytest
from execution_gateway.fake_gateway import FakeExecutionGateway
from execution_gateway import FakeExecutionGateway as FEG
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.gateway import ExecutionGateway
import execution_gateway


# ── helpers ────────────────────────────────────────────────────────────────

def _request(order_id: str = "ord-1", **kw) -> ExecutionRequest:
    defaults = dict(symbol="BTCUSDT", side="buy", order_type="market", quantity=0.01)
    return ExecutionRequest(order_id=order_id, **{**defaults, **kw})


def _result_accepted(order_id: str = "ord-1") -> ExecutionResult:
    return ExecutionResult(order_id=order_id, status="accepted")


def _result_rejected(order_id: str = "ord-1") -> ExecutionResult:
    return ExecutionResult(order_id=order_id, status="rejected", error_message="insufficient margin")


def _result_filled(order_id: str = "ord-1") -> ExecutionResult:
    return ExecutionResult(order_id=order_id, status="filled", filled_quantity=0.01, average_price=60_000.0)


# ── importación pública ────────────────────────────────────────────────────

def test_import_from_fake_gateway_module():
    assert FakeExecutionGateway is not None


def test_import_from_package():
    assert FEG is FakeExecutionGateway


def test_in_all():
    assert "FakeExecutionGateway" in execution_gateway.__all__


# ── compatibilidad estructural ─────────────────────────────────────────────

def test_implements_gateway_protocol():
    gw = FakeExecutionGateway(result=_result_accepted())
    assert isinstance(gw, ExecutionGateway)


# ── last_request inicial ───────────────────────────────────────────────────

def test_last_request_is_none_initially():
    gw = FakeExecutionGateway(result=_result_accepted())
    assert gw.last_request is None


# ── comportamiento en ejecución válida ─────────────────────────────────────

def test_returns_configured_result():
    result = _result_accepted()
    gw = FakeExecutionGateway(result=result)
    returned = gw.execute(_request())
    assert returned is result


def test_saves_last_request():
    gw = FakeExecutionGateway(result=_result_accepted())
    req = _request()
    gw.execute(req)
    assert gw.last_request is req


def test_last_request_updated_on_second_call():
    gw = FakeExecutionGateway(result=_result_accepted("ord-1"))
    req1 = _request("ord-1")
    req2 = _request("ord-1", side="sell")
    gw.execute(req1)
    gw.execute(req2)
    assert gw.last_request is req2


# ── rechazo por order_id incorrecto ───────────────────────────────────────

def test_rejects_mismatched_order_id():
    gw = FakeExecutionGateway(result=_result_accepted("ord-1"))
    with pytest.raises(ValueError):
        gw.execute(_request("ord-99"))


def test_last_request_not_updated_on_mismatch():
    gw = FakeExecutionGateway(result=_result_accepted("ord-1"))
    with pytest.raises(ValueError):
        gw.execute(_request("ord-99"))
    assert gw.last_request is None


# ── inmutabilidad de contratos ─────────────────────────────────────────────

def test_does_not_modify_request():
    req = _request()
    gw = FakeExecutionGateway(result=_result_accepted())
    gw.execute(req)
    assert req.order_id == "ord-1"
    assert req.symbol == "BTCUSDT"


def test_does_not_modify_result():
    result = _result_accepted()
    gw = FakeExecutionGateway(result=result)
    gw.execute(_request())
    assert result.status == "accepted"
    assert result.order_id == "ord-1"


# ── distintos estados de resultado ────────────────────────────────────────

def test_works_with_accepted():
    result = _result_accepted()
    gw = FakeExecutionGateway(result=result)
    assert gw.execute(_request()).status == "accepted"


def test_works_with_rejected():
    result = _result_rejected()
    gw = FakeExecutionGateway(result=result)
    returned = gw.execute(_request())
    assert returned.status == "rejected"
    assert returned.error_message == "insufficient margin"


def test_works_with_filled():
    result = _result_filled()
    gw = FakeExecutionGateway(result=result)
    returned = gw.execute(_request())
    assert returned.status == "filled"
    assert returned.filled_quantity == 0.01
    assert returned.average_price == 60_000.0
