import phoenix_core
from phoenix_core import (
    __version__,
    Config, get_config,
    Event,
    Signal,
    Order,
    Trade,
    Portfolio,
    bot_id, signal_id, order_id, trade_id, event_id, portfolio_id, is_valid,
)


def test_import():
    assert phoenix_core is not None


def test_version():
    assert phoenix_core.__version__ == "0.1.0"


def test_version_direct():
    assert __version__ == "0.1.0"


def test_all_contains_public_exports():
    expected = {
        "__version__",
        "Config", "get_config",
        "Event",
        "Signal",
        "Order",
        "Trade",
        "Portfolio",
        "bot_id", "signal_id", "order_id", "trade_id", "event_id", "portfolio_id",
        "is_valid",
    }
    assert expected.issubset(set(phoenix_core.__all__))


def test_contracts_importable():
    assert Config is not None
    assert get_config is not None
    assert Event is not None
    assert Signal is not None
    assert Order is not None
    assert Trade is not None
    assert Portfolio is not None


def test_id_functions_importable():
    assert bot_id is not None
    assert signal_id is not None
    assert order_id is not None
    assert trade_id is not None
    assert event_id is not None
    assert portfolio_id is not None
    assert is_valid is not None
