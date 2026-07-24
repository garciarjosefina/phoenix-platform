import pytest
from phoenix_core.ids import (
    bot_id, signal_id, order_id, trade_id, event_id, is_valid,
)

GENERATORS = [
    ("bot", bot_id),
    ("signal", signal_id),
    ("order", order_id),
    ("trade", trade_id),
    ("event", event_id),
]


@pytest.mark.parametrize("prefix,gen", GENERATORS)
def test_returns_string(prefix, gen):
    assert isinstance(gen(), str)


@pytest.mark.parametrize("prefix,gen", GENERATORS)
def test_format(prefix, gen):
    value = gen()
    assert value.startswith(f"{prefix}_")
    suffix = value[len(prefix) + 1:]
    assert len(suffix) == 36  # UUID4 canonical form


@pytest.mark.parametrize("prefix,gen", GENERATORS)
def test_unique(prefix, gen):
    ids = {gen() for _ in range(100)}
    assert len(ids) == 100


@pytest.mark.parametrize("prefix,gen", GENERATORS)
def test_is_valid_accepts_generated(prefix, gen):
    assert is_valid(gen(), prefix)


@pytest.mark.parametrize("prefix,gen", GENERATORS)
def test_is_valid_rejects_wrong_prefix(prefix, gen):
    value = gen()
    wrong = "wrong_" + value.split("_", 1)[1]
    assert not is_valid(wrong, prefix)


@pytest.mark.parametrize("prefix,_", GENERATORS)
def test_is_valid_rejects_empty(prefix, _):
    assert not is_valid("", prefix)


@pytest.mark.parametrize("prefix,_", GENERATORS)
def test_is_valid_rejects_no_uuid(prefix, _):
    assert not is_valid(f"{prefix}_notauuid", prefix)


@pytest.mark.parametrize("prefix,_", GENERATORS)
def test_is_valid_rejects_non_string(prefix, _):
    assert not is_valid(None, prefix)
