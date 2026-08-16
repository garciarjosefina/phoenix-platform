import pytest

import execution_gateway
from execution_gateway.bybit_demo_exchange_state_reader_env_bootstrap import (
    bootstrap_bybit_demo_exchange_state_reader_from_env,
)
from execution_gateway.bybit_demo_exchange_state_reader_factory import (
    create_bybit_demo_exchange_state_reader,
)
from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.bybit_open_orders_reader import BybitOpenOrdersReader
from execution_gateway.bybit_positions_reader import BybitPositionsReader
from execution_gateway.bybit_wallet_balance_reader import BybitWalletBalanceReader
from execution_gateway.composite_exchange_state_reader import CompositeExchangeStateReader
from execution_gateway.configured_bybit_demo_exchange_state_reader_factory import (
    create_configured_bybit_demo_exchange_state_reader,
)
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError

_VALID_ENV = {
    "PHOENIX_BYBIT_DEMO_API_KEY": "demo-key",
    "PHOENIX_BYBIT_DEMO_API_SECRET": "demo-secret",
    "PHOENIX_BYBIT_RECV_WINDOW_MS": "5000",
    "PHOENIX_HTTP_TIMEOUT_SECONDS": "10",
}


class _FakePositionsReader(BybitPositionsReader):
    def __init__(self) -> None:
        pass


class _FakeOpenOrdersReader(BybitOpenOrdersReader):
    def __init__(self) -> None:
        pass


class _FakeWalletBalanceReader(BybitWalletBalanceReader):
    def __init__(self) -> None:
        pass


class TestCreateBybitDemoExchangeStateReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_exchange_state_reader")
        assert (
            execution_gateway.create_bybit_demo_exchange_state_reader
            is create_bybit_demo_exchange_state_reader
        )

    def test_in_all(self):
        assert "create_bybit_demo_exchange_state_reader" in execution_gateway.__all__

    def test_positions_reader_must_satisfy_protocol(self):
        with pytest.raises(TypeError, match="PositionsReader"):
            create_bybit_demo_exchange_state_reader(
                positions_reader=object(),
                open_orders_reader=_FakeOpenOrdersReader(),
                wallet_balance_reader=_FakeWalletBalanceReader(),
            )

    def test_returns_composite_exchange_state_reader(self):
        reader = create_bybit_demo_exchange_state_reader(
            positions_reader=_FakePositionsReader(),
            open_orders_reader=_FakeOpenOrdersReader(),
            wallet_balance_reader=_FakeWalletBalanceReader(),
        )
        assert isinstance(reader, CompositeExchangeStateReader)

    def test_preserves_readers_by_identity(self):
        p, o, w = _FakePositionsReader(), _FakeOpenOrdersReader(), _FakeWalletBalanceReader()
        reader = create_bybit_demo_exchange_state_reader(
            positions_reader=p, open_orders_reader=o, wallet_balance_reader=w,
        )
        assert reader._positions_reader is p
        assert reader._open_orders_reader is o
        assert reader._wallet_balance_reader is w

    def test_keyword_only(self):
        with pytest.raises(TypeError):
            create_bybit_demo_exchange_state_reader(
                _FakePositionsReader(), _FakeOpenOrdersReader(), _FakeWalletBalanceReader(),
            )

    def test_two_calls_return_distinct_instances(self):
        p, o, w = _FakePositionsReader(), _FakeOpenOrdersReader(), _FakeWalletBalanceReader()
        r1 = create_bybit_demo_exchange_state_reader(
            positions_reader=p, open_orders_reader=o, wallet_balance_reader=w,
        )
        r2 = create_bybit_demo_exchange_state_reader(
            positions_reader=p, open_orders_reader=o, wallet_balance_reader=w,
        )
        assert r1 is not r2


class TestCreateConfiguredBybitDemoExchangeStateReader:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_configured_bybit_demo_exchange_state_reader")
        assert (
            execution_gateway.create_configured_bybit_demo_exchange_state_reader
            is create_configured_bybit_demo_exchange_state_reader
        )

    def test_in_all(self):
        assert "create_configured_bybit_demo_exchange_state_reader" in execution_gateway.__all__

    def test_config_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitDemoExecutionConfig"):
            create_configured_bybit_demo_exchange_state_reader(config=object())

    def test_returns_composite_exchange_state_reader(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        reader = create_configured_bybit_demo_exchange_state_reader(config=config)
        assert isinstance(reader, CompositeExchangeStateReader)

    def test_sub_readers_are_correct_bybit_types(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        reader = create_configured_bybit_demo_exchange_state_reader(config=config)
        assert isinstance(reader._positions_reader, BybitPositionsReader)
        assert isinstance(reader._open_orders_reader, BybitOpenOrdersReader)
        assert isinstance(reader._wallet_balance_reader, BybitWalletBalanceReader)

    def test_invalid_recv_window_rejected(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        object.__setattr__(config, "recv_window_ms", -1)
        with pytest.raises(ValueError, match="recv_window_ms must be > 0"):
            create_configured_bybit_demo_exchange_state_reader(config=config)

    def test_invalid_timeout_rejected(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        object.__setattr__(config, "timeout_seconds", 0)
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            create_configured_bybit_demo_exchange_state_reader(config=config)

    def test_does_not_construct_execution_gateway(self):
        import inspect
        import execution_gateway.configured_bybit_demo_exchange_state_reader_factory as module
        src = inspect.getsource(module)
        assert "BybitExecutionGateway" not in src
        assert "BybitDemoClient" not in src
        assert "create_order" not in src

    def test_does_not_reference_instrument_metadata(self):
        import inspect
        import execution_gateway.configured_bybit_demo_exchange_state_reader_factory as module
        src = inspect.getsource(module)
        assert "InstrumentMetadata" not in src
        assert "instrument_metadata" not in src

    def test_reuses_existing_configured_factories_not_lower_primitives(self):
        import inspect
        import execution_gateway.configured_bybit_demo_exchange_state_reader_factory as module
        src = inspect.getsource(module)
        assert "create_configured_bybit_demo_positions_reader" in src
        assert "create_configured_bybit_demo_open_orders_reader" in src
        assert "create_configured_bybit_demo_wallet_balance_reader" in src
        # No reconstruye el GET stack a mano -- delega en las tres
        # factories configuradas ya aceptadas.
        assert "UrllibGetHttpTransport" not in src
        assert "BybitPrivateGetApi" not in src
        assert "create_bybit_authenticator" not in src

    def test_two_calls_return_distinct_instances(self):
        config = BybitDemoExecutionConfig(
            api_key="k", api_secret="s", recv_window_ms=5000, timeout_seconds=10,
        )
        r1 = create_configured_bybit_demo_exchange_state_reader(config=config)
        r2 = create_configured_bybit_demo_exchange_state_reader(config=config)
        assert r1 is not r2
        assert r1._positions_reader is not r2._positions_reader


class TestBootstrap:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "bootstrap_bybit_demo_exchange_state_reader_from_env")
        assert (
            execution_gateway.bootstrap_bybit_demo_exchange_state_reader_from_env
            is bootstrap_bybit_demo_exchange_state_reader_from_env
        )

    def test_in_all(self):
        assert "bootstrap_bybit_demo_exchange_state_reader_from_env" in execution_gateway.__all__

    def test_keyword_only_environ(self):
        with pytest.raises(TypeError):
            bootstrap_bybit_demo_exchange_state_reader_from_env(_VALID_ENV)

    def test_environ_defaults_to_none(self):
        import inspect
        sig = inspect.signature(bootstrap_bybit_demo_exchange_state_reader_from_env)
        assert sig.parameters["environ"].default is None

    def test_returns_composite_exchange_state_reader(self):
        reader = bootstrap_bybit_demo_exchange_state_reader_from_env(environ=_VALID_ENV)
        assert isinstance(reader, CompositeExchangeStateReader)

    def test_missing_api_key_raises_environment_configuration_error(self):
        env = {k: v for k, v in _VALID_ENV.items() if k != "PHOENIX_BYBIT_DEMO_API_KEY"}
        with pytest.raises(EnvironmentConfigurationError, match="PHOENIX_BYBIT_DEMO_API_KEY"):
            bootstrap_bybit_demo_exchange_state_reader_from_env(environ=env)

    def test_reuses_same_loader_as_other_readers_bootstrap(self):
        import inspect
        import execution_gateway.bybit_demo_exchange_state_reader_env_bootstrap as module
        src = inspect.getsource(module)
        assert "load_bybit_demo_execution_config_from_env" in src
        assert "os.environ" not in src
        assert "PHOENIX_BYBIT_DEMO_API_KEY" not in src

    def test_two_calls_build_distinct_graphs(self):
        r1 = bootstrap_bybit_demo_exchange_state_reader_from_env(environ=_VALID_ENV)
        r2 = bootstrap_bybit_demo_exchange_state_reader_from_env(environ=_VALID_ENV)
        assert r1 is not r2

    def test_no_new_environment_variables_introduced(self):
        import inspect
        import execution_gateway.bybit_demo_exchange_state_reader_env_bootstrap as bootstrap_module
        import execution_gateway.configured_bybit_demo_exchange_state_reader_factory as configured_module
        for module in (bootstrap_module, configured_module):
            code_lines = [
                line for line in inspect.getsource(module).splitlines()
                if not line.strip().startswith("#")
            ]
            code = "\n".join(code_lines)
            assert "PHOENIX_" not in code
