import pytest
from datetime import timezone

from phoenix_core.ids import bot_id, signal_id, is_valid
from phoenix_core.orders import Order


def _bid() -> str:
    return bot_id()


def _sid() -> str:
    return signal_id()


def _market(**kw) -> Order:
    defaults = dict(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
                    side="buy", order_type="market", quantity=0.01)
    return Order(**{**defaults, **kw})


def _limit(**kw) -> Order:
    defaults = dict(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
                    side="buy", order_type="limit", quantity=0.01, price=50_000.0)
    return Order(**{**defaults, **kw})


# --- creación válida ---

def test_valid_market_buy():
    o = _market(side="buy")
    assert o.side == "buy" and o.order_type == "market"


def test_valid_market_sell():
    o = _market(side="sell")
    assert o.side == "sell" and o.order_type == "market"


def test_valid_limit_buy():
    o = _limit(side="buy")
    assert o.side == "buy" and o.order_type == "limit" and o.price == 50_000.0


def test_valid_limit_sell():
    o = _limit(side="sell")
    assert o.side == "sell" and o.order_type == "limit"


# --- generación automática ---

def test_order_id_generated():
    assert is_valid(_market().order_id, "order")


def test_two_orders_have_different_ids():
    assert _market().order_id != _market().order_id


def test_timestamp_utc():
    assert _market().timestamp.tzinfo == timezone.utc


def test_status_default():
    assert _market().status == "created"


def test_metadata_empty_by_default():
    assert _market().metadata == {}


# --- serialización ---

def test_to_dict_keys():
    expected = {"order_id", "signal_id", "bot_id", "symbol", "side",
                "order_type", "quantity", "price", "status", "timestamp", "metadata"}
    assert set(_market().to_dict()) == expected


def test_to_dict_timestamp_iso8601():
    ts = _market().to_dict()["timestamp"]
    assert isinstance(ts, str) and "T" in ts and ts.endswith("+00:00")


def test_to_dict_market_price_is_none():
    assert _market().to_dict()["price"] is None


def test_to_dict_limit_price_preserved():
    assert _limit().to_dict()["price"] == 50_000.0


# --- rechazos ---

def test_rejects_invalid_signal_id():
    with pytest.raises(ValueError):
        Order(signal_id="bad", bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="market", quantity=0.01)


def test_rejects_invalid_bot_id():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id="bad", symbol="BTCUSDT",
              side="buy", order_type="market", quantity=0.01)


def test_rejects_empty_symbol():
    with pytest.raises(ValueError):
        _market(symbol="")


def test_rejects_invalid_side():
    with pytest.raises(ValueError):
        _market(side="long")


def test_rejects_invalid_order_type():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="stop", quantity=0.01)


def test_rejects_zero_quantity():
    with pytest.raises(ValueError):
        _market(quantity=0)


def test_rejects_negative_quantity():
    with pytest.raises(ValueError):
        _market(quantity=-1)


def test_rejects_limit_without_price():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="limit", quantity=0.01)


def test_rejects_limit_with_zero_price():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="limit", quantity=0.01, price=0.0)


def test_rejects_market_with_price():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="market", quantity=0.01, price=100.0)


def test_rejects_invalid_status():
    with pytest.raises(ValueError):
        Order(signal_id=_sid(), bot_id=_bid(), symbol="BTCUSDT",
              side="buy", order_type="market", quantity=0.01, status="open")


def test_rejects_metadata_list():
    with pytest.raises(TypeError):
        _market(metadata=[1, 2])


def test_immutability():
    o = _market()
    with pytest.raises(AttributeError):
        o.status = "open"
