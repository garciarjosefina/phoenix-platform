import pytest
from phoenix_core import __version__
from phoenix_core.config import Config, get_config


def test_get_config_returns_config():
    assert isinstance(get_config(), Config)


def test_default_environment():
    assert get_config().environment == "development"


def test_default_debug():
    assert get_config().debug is False


def test_default_version_matches_package():
    assert get_config().version == __version__


def test_immutability():
    cfg = get_config()
    with pytest.raises(AttributeError):
        cfg.environment = "production"
