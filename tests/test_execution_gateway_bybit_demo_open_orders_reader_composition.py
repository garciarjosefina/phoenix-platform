import pytest

import execution_gateway
from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.bybit_demo_open_orders_reader_env_bootstrap import (
    bootstrap_bybit_demo_open_orders_reader_from_env,
)
from execution_gateway.bybit_demo_open_orders_reader_factory import create_bybit_demo_open_orders_reader
from execution_gateway.bybit_open_orders_reader import BybitOpenOrdersReader
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.configured_bybit_demo_open_orders_reader_factory import (
    create_configured_bybit_demo_open_orders_reader,
)
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError

_VALID_ENV = {
    "PHOENIX_BYBIT_DEMO_API_KEY": "demo-key",
    "PHOENIX_BYBIT_DEMO_API_SECRET": "demo-secret",
    "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
    "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
}


class _FakePrivateGetApi(BybitPrivateGetApi):
    def __init__(self) -> None:
        pass


class TestCreateBybitDemoOpenOrdersReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_open_orders_reader")
        assert (
            execution_gateway.create_bybit_demo_open_orders_reader
            is create_bybit_demo_open_orders_reader
        )

    def test_in_all(self):
        assert "create_bybit_demo_open_orders_reader" in execution_gateway.__all__

    def test_private_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetApi"):
            create_bybit_demo_open_orders_reader(private_get_api=object())

    def test_returns_bybit_open_orders_reader(self):
        reader = create_bybit_demo_open_orders_reader(private_get_api=_FakePrivateGetApi())
        assert isinstance(reader, BybitOpenOrdersReader)

    def test_preserves_private_get_api_by_identity(self):
        api = _FakePrivateGetApi()
        reader = create_bybit_demo_open_orders_reader(private_get_api=api)
        assert reader._private_get_api is api

    def test_uses_demo_base_url(self):
        reader = create_bybit_demo_open_orders_reader(private_get_api=_FakePrivateGetApi())
        assert reader._url_builder._base_url == "https://api-demo.bybit.com"

    def test_keyword_only(self):
        with pytest.raises(TypeError):
            create_bybit_demo_open_orders_reader(_FakePrivateGetApi())

    def test_two_calls_return_distinct_instances(self):
        api = _FakePrivateGetApi()
        r1 = create_bybit_demo_open_orders_reader(private_get_api=api)
        r2 = create_bybit_demo_open_orders_reader(private_get_api=api)
        assert r1 is not r2


class TestCreateConfiguredBybitDemoOpenOrdersReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_configured_bybit_demo_open_orders_reader")
        assert (
            execution_gateway.create_configured_bybit_demo_open_orders_reader
            is create_configured_bybit_demo_open_orders_reader
        )

    def test_in_all(self):
        assert "create_configured_bybit_demo_open_orders_reader" in execution_gateway.__all__

    def test_config_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitDemoExecutionConfig"):
            create_configured_bybit_demo_open_orders_reader(config=object())

    def test_returns_bybit_open_orders_reader(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        reader = create_configured_bybit_demo_open_orders_reader(config=config)
        assert isinstance(reader, BybitOpenOrdersReader)

    def test_invalid_recv_window_rejected(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        object.__setattr__(config, "recv_window_ms", -1)
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            create_configured_bybit_demo_open_orders_reader(config=config)

    def test_invalid_timeout_rejected(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        object.__setattr__(config, "timeout_seconds", 0)
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_configured_bybit_demo_open_orders_reader(config=config)

    def test_does_not_construct_execution_gateway(self):
        import inspect
        import execution_gateway.configured_bybit_demo_open_orders_reader_factory as module
        src = inspect.getsource(module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src
        assert "create_order" not in src

    def test_two_calls_return_distinct_instances(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        r1 = create_configured_bybit_demo_open_orders_reader(config=config)
        r2 = create_configured_bybit_demo_open_orders_reader(config=config)
        assert r1 is not r2


class TestBootstrap:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "bootstrap_bybit_demo_open_orders_reader_from_env")
        assert (
            execution_gateway.bootstrap_bybit_demo_open_orders_reader_from_env
            is bootstrap_bybit_demo_open_orders_reader_from_env
        )

    def test_in_all(self):
        assert "bootstrap_bybit_demo_open_orders_reader_from_env" in execution_gateway.__all__

    def test_keyword_only_environ(self):
        with pytest.raises(TypeError):
            bootstrap_bybit_demo_open_orders_reader_from_env(_VALID_ENV)

    def test_environ_defaults_to_none(self):
        import inspect
        sig = inspect.signature(bootstrap_bybit_demo_open_orders_reader_from_env)
        assert sig.parameters["environ"].default is None

    def test_returns_bybit_open_orders_reader(self):
        reader = bootstrap_bybit_demo_open_orders_reader_from_env(environ=_VALID_ENV)
        assert isinstance(reader, BybitOpenOrdersReader)

    def test_missing_api_key_raises_environment_configuration_error(self):
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            bootstrap_bybit_demo_open_orders_reader_from_env(environ=env)

    def test_reuses_same_loader_as_positions_reader_bootstrap(self):
        import inspect
        import execution_gateway.bybit_demo_open_orders_reader_env_bootstrap as module
        src = inspect.getsource(module)
        assert "load_bybit_demo_execution_config_from_env" in src
        assert "os.environ" not in src
        assert "PHOENIX_BYBIT_DEMO_API_KEY" not in src

    def test_two_calls_build_distinct_graphs(self):
        r1 = bootstrap_bybit_demo_open_orders_reader_from_env(environ=_VALID_ENV)
        r2 = bootstrap_bybit_demo_open_orders_reader_from_env(environ=_VALID_ENV)
        assert r1 is not r2
