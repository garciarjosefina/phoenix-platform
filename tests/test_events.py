import pytest
from datetime import timezone

from phoenix_core.events import Event
from phoenix_core.ids import is_valid


def test_valid_creation():
    e = Event(event_type="bot.started", source="fib-bot")
    assert e.event_type == "bot.started"
    assert e.source == "fib-bot"


def test_event_id_generated():
    e = Event(event_type="test", source="test")
    assert is_valid(e.event_id, "event")


def test_two_events_have_different_ids():
    a = Event(event_type="test", source="test")
    b = Event(event_type="test", source="test")
    assert a.event_id != b.event_id


def test_timestamp_utc():
    e = Event(event_type="test", source="test")
    assert e.timestamp.tzinfo == timezone.utc


def test_payload_empty_by_default():
    e = Event(event_type="test", source="test")
    assert e.payload == {}


def test_payload_accepted():
    e = Event(event_type="test", source="test", payload={"k": "v"})
    assert e.payload == {"k": "v"}


def test_to_dict_keys():
    e = Event(event_type="test", source="test", payload={"x": 1})
    d = e.to_dict()
    assert set(d) == {"event_id", "event_type", "source", "timestamp", "payload"}


def test_to_dict_timestamp_iso8601():
    e = Event(event_type="test", source="test")
    ts = e.to_dict()["timestamp"]
    assert isinstance(ts, str)
    assert "T" in ts
    assert ts.endswith("+00:00")


def test_to_dict_preserves_fields():
    e = Event(event_type="sig.fired", source="engine", payload={"price": 100})
    d = e.to_dict()
    assert d["event_id"] == e.event_id
    assert d["event_type"] == "sig.fired"
    assert d["source"] == "engine"
    assert d["payload"] == {"price": 100}


def test_rejects_empty_event_type():
    with pytest.raises(ValueError):
        Event(event_type="", source="test")


def test_rejects_empty_source():
    with pytest.raises(ValueError):
        Event(event_type="test", source="")


def test_rejects_payload_string():
    with pytest.raises(TypeError):
        Event(event_type="test", source="test", payload="bad")


def test_rejects_payload_list():
    with pytest.raises(TypeError):
        Event(event_type="test", source="test", payload=[1, 2])


def test_immutability():
    e = Event(event_type="test", source="test")
    with pytest.raises(AttributeError):
        e.event_type = "other"
