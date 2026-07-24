import pytest
from datetime import timezone

from phoenix_core.ids import bot_id, is_valid
from phoenix_core.signals import Signal


def _valid_bot_id() -> str:
    return bot_id()


def test_valid_long():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    assert s.side == "long"


def test_valid_short():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="short", timeframe="15m")
    assert s.side == "short"


def test_signal_id_generated():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    assert is_valid(s.signal_id, "signal")


def test_two_signals_have_different_ids():
    bid = _valid_bot_id()
    a = Signal(bot_id=bid, symbol="BTCUSDT", side="long", timeframe="15m")
    b = Signal(bot_id=bid, symbol="BTCUSDT", side="long", timeframe="15m")
    assert a.signal_id != b.signal_id


def test_timestamp_utc():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    assert s.timestamp.tzinfo == timezone.utc


def test_metadata_empty_by_default():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    assert s.metadata == {}


def test_to_dict_keys():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    assert set(s.to_dict()) == {"signal_id", "bot_id", "symbol", "side", "timeframe", "timestamp", "metadata"}


def test_to_dict_timestamp_iso8601():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    ts = s.to_dict()["timestamp"]
    assert isinstance(ts, str) and "T" in ts and ts.endswith("+00:00")


def test_to_dict_preserves_fields():
    bid = _valid_bot_id()
    s = Signal(bot_id=bid, symbol="XAUUSDT", side="short", timeframe="5m", metadata={"score": 9})
    d = s.to_dict()
    assert d["bot_id"] == bid
    assert d["symbol"] == "XAUUSDT"
    assert d["side"] == "short"
    assert d["timeframe"] == "5m"
    assert d["metadata"] == {"score": 9}


def test_rejects_invalid_bot_id():
    with pytest.raises(ValueError):
        Signal(bot_id="not-a-bot-id", symbol="BTCUSDT", side="long", timeframe="15m")


def test_rejects_empty_symbol():
    with pytest.raises(ValueError):
        Signal(bot_id=_valid_bot_id(), symbol="", side="long", timeframe="15m")


def test_rejects_invalid_side():
    with pytest.raises(ValueError):
        Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="buy", timeframe="15m")


def test_rejects_empty_timeframe():
    with pytest.raises(ValueError):
        Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="")


def test_rejects_metadata_list():
    with pytest.raises(TypeError):
        Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m", metadata=[])


def test_immutability():
    s = Signal(bot_id=_valid_bot_id(), symbol="BTCUSDT", side="long", timeframe="15m")
    with pytest.raises(AttributeError):
        s.side = "short"
