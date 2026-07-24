import pytest
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway import ExecutionRequest as EReq, ExecutionResult as ERes


# ── helpers ────────────────────────────────────────────────────────────────

def _market(**kw) -> ExecutionRequest:
    defaults = dict(order_id="ord-1", symbol="BTCUSDT", side="buy",
                    order_type="market", quantity=0.01)
    return ExecutionRequest(**{**defaults, **kw})


def _limit(**kw) -> ExecutionRequest:
    defaults = dict(order_id="ord-1", symbol="BTCUSDT", side="buy",
                    order_type="limit", quantity=0.01, price=60_000.0)
    return ExecutionRequest(**{**defaults, **kw})


def _result(**kw) -> ExecutionResult:
    defaults = dict(order_id="ord-1", status="accepted")
    return ExecutionResult(**{**defaults, **kw})


# ── importación pública ────────────────────────────────────────────────────

def test_import_from_contracts():
    assert ExecutionRequest is not None
    assert ExecutionResult is not None


def test_import_from_package():
    assert EReq is ExecutionRequest
    assert ERes is ExecutionResult


# ── ExecutionRequest — creación válida ─────────────────────────────────────

def test_valid_market_buy():
    r = _market(side="buy")
    assert r.side == "buy" and r.order_type == "market" and r.price is None


def test_valid_market_sell():
    r = _market(side="sell")
    assert r.side == "sell"


def test_valid_limit_buy():
    r = _limit(side="buy")
    assert r.price == 60_000.0 and r.order_type == "limit"


def test_valid_limit_sell():
    r = _limit(side="sell")
    assert r.side == "sell"


# ── ExecutionRequest — rechazos ────────────────────────────────────────────

def test_request_rejects_empty_order_id():
    with pytest.raises(ValueError):
        _market(order_id="")


def test_request_rejects_empty_symbol():
    with pytest.raises(ValueError):
        _market(symbol="")


def test_request_rejects_invalid_side():
    with pytest.raises(ValueError):
        _market(side="long")


def test_request_rejects_invalid_order_type():
    with pytest.raises(ValueError):
        ExecutionRequest(order_id="x", symbol="BTC", side="buy",
                         order_type="stop", quantity=1.0)


def test_request_rejects_zero_quantity():
    with pytest.raises(ValueError):
        _market(quantity=0)


def test_request_rejects_negative_quantity():
    with pytest.raises(ValueError):
        _market(quantity=-0.5)


def test_request_rejects_limit_without_price():
    with pytest.raises(ValueError):
        ExecutionRequest(order_id="x", symbol="BTC", side="buy",
                         order_type="limit", quantity=1.0)


def test_request_rejects_limit_with_zero_price():
    with pytest.raises(ValueError):
        _limit(price=0.0)


def test_request_rejects_limit_with_negative_price():
    with pytest.raises(ValueError):
        _limit(price=-1.0)


def test_request_rejects_market_with_price():
    with pytest.raises(ValueError):
        _market(price=50_000.0)


# ── ExecutionRequest — inmutabilidad ───────────────────────────────────────

def test_request_immutability():
    r = _market()
    with pytest.raises(AttributeError):
        r.side = "sell"


# ── ExecutionResult — estados válidos ──────────────────────────────────────

def test_result_accepted():
    r = _result(status="accepted")
    assert r.status == "accepted"


def test_result_cancelled():
    r = _result(status="cancelled")
    assert r.status == "cancelled"


def test_result_rejected():
    r = _result(status="rejected", error_message="insufficient margin")
    assert r.status == "rejected" and r.error_message == "insufficient margin"


def test_result_partially_filled():
    r = _result(status="partially_filled", filled_quantity=0.005, average_price=60_000.0)
    assert r.status == "partially_filled"


def test_result_filled():
    r = _result(status="filled", filled_quantity=0.01, average_price=60_000.0)
    assert r.status == "filled"


# ── ExecutionResult — valores por defecto ──────────────────────────────────

def test_result_default_filled_quantity():
    assert _result().filled_quantity == 0.0


def test_result_default_exchange_order_id():
    assert _result().exchange_order_id is None


def test_result_default_average_price():
    assert _result().average_price is None


def test_result_default_error_message():
    assert _result().error_message is None


# ── ExecutionResult — rechazos ─────────────────────────────────────────────

def test_result_rejects_empty_order_id():
    with pytest.raises(ValueError):
        _result(order_id="")


def test_result_rejects_invalid_status():
    with pytest.raises(ValueError):
        _result(status="open")


def test_result_rejects_negative_filled_quantity():
    with pytest.raises(ValueError):
        _result(filled_quantity=-0.01)


def test_result_rejects_zero_average_price():
    with pytest.raises(ValueError):
        _result(average_price=0.0)


def test_result_rejects_negative_average_price():
    with pytest.raises(ValueError):
        _result(average_price=-1.0)


def test_result_rejects_rejected_without_error_message():
    with pytest.raises(ValueError):
        _result(status="rejected")


def test_result_rejects_accepted_with_error_message():
    with pytest.raises(ValueError):
        _result(status="accepted", error_message="oops")


def test_result_rejects_filled_with_zero_quantity():
    with pytest.raises(ValueError):
        _result(status="filled", filled_quantity=0.0, average_price=60_000.0)


def test_result_rejects_filled_without_average_price():
    with pytest.raises(ValueError):
        _result(status="filled", filled_quantity=0.01)


def test_result_rejects_partially_filled_without_average_price():
    with pytest.raises(ValueError):
        _result(status="partially_filled", filled_quantity=0.005)


# ── ExecutionResult — inmutabilidad ───────────────────────────────────────

def test_result_immutability():
    r = _result()
    with pytest.raises(AttributeError):
        r.status = "cancelled"
