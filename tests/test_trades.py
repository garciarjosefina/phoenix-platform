import pytest
from datetime import timezone

from phoenix_core.ids import bot_id, signal_id, order_id, is_valid
from phoenix_core.trades import Trade


def _oid() -> str:
    return order_id()

def _sid() -> str:
    return signal_id()

def _bid() -> str:
    return bot_id()


def _trade(**kw) -> Trade:
    defaults = dict(order_id=_oid(), signal_id=_sid(), bot_id=_bid(),
                    symbol="BTCUSDT", side="long", quantity=0.01, entry_price=60_000.0)
    return Trade(**{**defaults, **kw})


# --- creación válida ---

def test_valid_long():
    t = _trade(side="long")
    assert t.side == "long"


def test_valid_short():
    t = _trade(side="short")
    assert t.side == "short"


# --- generación automática ---

def test_trade_id_generated():
    assert is_valid(_trade().trade_id, "trade")


def test_two_trades_have_different_ids():
    assert _trade().trade_id != _trade().trade_id


def test_opened_at_utc():
    assert _trade().opened_at.tzinfo == timezone.utc


def test_metadata_empty_by_default():
    assert _trade().metadata == {}


# --- serialización ---

def test_to_dict_keys():
    expected = {"trade_id", "order_id", "signal_id", "bot_id", "symbol",
                "side", "quantity", "entry_price", "opened_at", "metadata"}
    assert set(_trade().to_dict()) == expected


def test_to_dict_opened_at_iso8601():
    ts = _trade().to_dict()["opened_at"]
    assert isinstance(ts, str) and "T" in ts and ts.endswith("+00:00")


def test_to_dict_preserves_fields():
    oid, sid, bid = _oid(), _sid(), _bid()
    t = _trade(order_id=oid, signal_id=sid, bot_id=bid,
               symbol="XAUUSDT", side="short", quantity=0.5, entry_price=2_300.0,
               metadata={"regime": "bear"})
    d = t.to_dict()
    assert d["order_id"] == oid
    assert d["signal_id"] == sid
    assert d["bot_id"] == bid
    assert d["symbol"] == "XAUUSDT"
    assert d["side"] == "short"
    assert d["quantity"] == 0.5
    assert d["entry_price"] == 2_300.0
    assert d["metadata"] == {"regime": "bear"}


# --- rechazos ---

def test_rejects_invalid_order_id():
    with pytest.raises(ValueError):
        _trade(order_id="bad")


def test_rejects_invalid_signal_id():
    with pytest.raises(ValueError):
        _trade(signal_id="bad")


def test_rejects_invalid_bot_id():
    with pytest.raises(ValueError):
        _trade(bot_id="bad")


def test_rejects_empty_symbol():
    with pytest.raises(ValueError):
        _trade(symbol="")


def test_rejects_invalid_side():
    with pytest.raises(ValueError):
        _trade(side="buy")


def test_rejects_zero_quantity():
    with pytest.raises(ValueError):
        _trade(quantity=0)


def test_rejects_negative_quantity():
    with pytest.raises(ValueError):
        _trade(quantity=-0.01)


def test_rejects_zero_entry_price():
    with pytest.raises(ValueError):
        _trade(entry_price=0)


def test_rejects_negative_entry_price():
    with pytest.raises(ValueError):
        _trade(entry_price=-1.0)


def test_rejects_metadata_string():
    with pytest.raises(TypeError):
        _trade(metadata="bad")


def test_immutability():
    t = _trade()
    with pytest.raises(AttributeError):
        t.side = "short"
