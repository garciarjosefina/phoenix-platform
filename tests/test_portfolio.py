import pytest
from datetime import timezone

from phoenix_core.ids import bot_id, is_valid
from phoenix_core.portfolio import Portfolio


def _portfolio(**kw) -> Portfolio:
    defaults = dict(name="main")
    return Portfolio(**{**defaults, **kw})


# --- creación válida ---

def test_valid_creation():
    p = _portfolio()
    assert p.name == "main"


def test_valid_creation_with_bots():
    bids = (bot_id(), bot_id())
    p = _portfolio(bot_ids=bids)
    assert p.bot_ids == bids


# --- generación automática ---

def test_portfolio_id_generated():
    assert is_valid(_portfolio().portfolio_id, "portfolio")


def test_two_portfolios_have_different_ids():
    assert _portfolio().portfolio_id != _portfolio().portfolio_id


def test_created_at_utc():
    assert _portfolio().created_at.tzinfo == timezone.utc


def test_bot_ids_empty_by_default():
    assert _portfolio().bot_ids == ()


def test_metadata_empty_by_default():
    assert _portfolio().metadata == {}


# --- serialización ---

def test_to_dict_keys():
    expected = {"portfolio_id", "name", "created_at", "bot_ids", "metadata"}
    assert set(_portfolio().to_dict()) == expected


def test_to_dict_created_at_iso8601():
    ts = _portfolio().to_dict()["created_at"]
    assert isinstance(ts, str) and "T" in ts and ts.endswith("+00:00")


def test_to_dict_bot_ids_as_list():
    bids = (bot_id(), bot_id())
    d = _portfolio(bot_ids=bids).to_dict()
    assert isinstance(d["bot_ids"], list)
    assert d["bot_ids"] == list(bids)


def test_to_dict_preserves_name_and_metadata():
    d = _portfolio(name="alpha", metadata={"risk": "low"}).to_dict()
    assert d["name"] == "alpha"
    assert d["metadata"] == {"risk": "low"}


# --- rechazos ---

def test_rejects_empty_name():
    with pytest.raises(ValueError):
        _portfolio(name="")


def test_rejects_invalid_bot_id_in_tuple():
    with pytest.raises(ValueError):
        _portfolio(bot_ids=(bot_id(), "not-a-bot-id"))


def test_rejects_metadata_list():
    with pytest.raises(TypeError):
        _portfolio(metadata=[1, 2])


def test_rejects_metadata_string():
    with pytest.raises(TypeError):
        _portfolio(metadata="bad")


# --- inmutabilidad ---

def test_immutability():
    p = _portfolio()
    with pytest.raises(AttributeError):
        p.name = "other"
