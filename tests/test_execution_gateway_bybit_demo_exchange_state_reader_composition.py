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


def _config_fingerprint(reader):
    # Extrae, del GRAFO DE OBJETOS REAL construido por la factory
    # configurada (no de source code ni de mocks), los cinco valores que
    # determinan contra qué cuenta/entorno autentica un reader privado.
    # Misma ruta de atributos para los tres readers privados (Positions/
    # OpenOrders/Wallet), porque los tres se construyen con el mismo
    # patrón GET privado (BybitPrivateGetApi -> BybitPrivateGetRequestSender
    # -> StandardBybitAuthenticator -> BybitDemoCredentials).
    sender = reader._private_get_api._sender
    return {
        "api_key": sender._authenticator._credentials.api_key,
        "api_secret": sender._authenticator._credentials.api_secret,
        "recv_window_ms": sender._authenticator._recv_window_ms,
        "timeout_seconds": sender._request_executor._timeout_seconds,
        "base_url": reader._url_builder._base_url,
    }


class TestConfigCoherenceAcrossSubReaders:
    """Hallazgo IMPORTANTE-1 de la auditoría adversarial independiente del
    Hito 3.74: produccion ya construye los tres sub-readers a partir del
    mismo BybitDemoExecutionConfig (verificado conductualmente por la
    auditoria: os.environ se lee una sola vez, el mismo objeto config se
    pasa a las tres sub-factories configuradas), pero nada en la suite
    aseveraba ese hecho -- un mutante que hiciera que Wallet autenticara
    contra una cuenta distinta sobrevivia los 173 tests del hito. Estos
    tests convierten esa coherencia, ya correcta en producción, en una
    propiedad protegida contra regresión. No se agrega ninguna validación
    nueva en tiempo de ejecución -- la factory ya la garantiza hoy."""

    def _build(self, **overrides):
        defaults = dict(
            api_key="CONFIG-KEY-AAA", api_secret="CONFIG-SECRET-BBB",
            recv_window_ms=5432, timeout_seconds=17,
        )
        defaults.update(overrides)
        config = BybitDemoExecutionConfig(**defaults)
        reader = create_configured_bybit_demo_exchange_state_reader(config=config)
        return (
            _config_fingerprint(reader._positions_reader),
            _config_fingerprint(reader._open_orders_reader),
            _config_fingerprint(reader._wallet_balance_reader),
        )

    def test_all_three_readers_share_same_api_key(self):
        p, o, w = self._build()
        assert p["api_key"] == o["api_key"] == w["api_key"] == "CONFIG-KEY-AAA"

    def test_all_three_readers_share_same_api_secret(self):
        p, o, w = self._build()
        assert p["api_secret"] == o["api_secret"] == w["api_secret"] == "CONFIG-SECRET-BBB"

    def test_all_three_readers_share_same_recv_window_ms(self):
        p, o, w = self._build()
        assert p["recv_window_ms"] == o["recv_window_ms"] == w["recv_window_ms"] == 5432

    def test_all_three_readers_share_same_timeout_seconds(self):
        p, o, w = self._build()
        assert p["timeout_seconds"] == o["timeout_seconds"] == w["timeout_seconds"] == 17

    def test_all_three_readers_share_same_demo_base_url(self):
        p, o, w = self._build()
        assert p["base_url"] == o["base_url"] == w["base_url"]
        assert p["base_url"] == "https://api-demo.bybit.com"
        assert "mainnet" not in p["base_url"] and "api.bybit.com" != p["base_url"].split("//")[-1]

    def test_full_fingerprint_identical_across_all_three_readers(self):
        # Aseveracion conjunta: ningun campo puede divergir entre los
        # tres readers de una misma ronda -- una configuracion hibrida
        # (una cuenta para Wallet, otra para Positions/OpenOrders) no
        # debe poder colarse silenciosamente.
        p, o, w = self._build(
            api_key="K2", api_secret="S2", recv_window_ms=9999, timeout_seconds=42,
        )
        assert p == o == w

    def test_distinct_configs_produce_distinct_fingerprints(self):
        # Control negativo: confirma que el fingerprint realmente
        # distingue configuraciones distintas (no es una tautologia que
        # siempre compara igual a si misma).
        p1, _, _ = self._build(api_key="ACCOUNT-A")
        p2, _, _ = self._build(api_key="ACCOUNT-B")
        assert p1["api_key"] != p2["api_key"]


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

    def test_environ_read_exactly_once_per_key_not_once_per_subreader(self):
        # Conductual, no de source: si el bootstrap releyera el entorno de
        # forma independiente para cada uno de los tres sub-readers, cada
        # clave se leeria 3 veces en vez de 1 -- y una mutacion del
        # entorno entre esas lecturas podria producir una ronda con
        # readers autenticados contra configuraciones distintas.

        class _CountingEnviron(dict):
            def __init__(self, data):
                super().__init__(data)
                self.reads = []

            def __getitem__(self, k):
                self.reads.append(k)
                return super().__getitem__(k)

            def get(self, k, default=None):
                self.reads.append(k)
                return super().get(k, default)

        spy_env = _CountingEnviron(_VALID_ENV)
        bootstrap_bybit_demo_exchange_state_reader_from_env(environ=spy_env)
        key_reads = [k for k in spy_env.reads if k == "PHOENIX_BYBIT_DEMO_API_KEY"]
        assert len(key_reads) == 1

    def test_all_three_sub_readers_share_config_loaded_from_same_environ_round(self):
        # Extremo a extremo desde la funcion publica de bootstrap (no
        # desde la factory configurada directamente): confirma que la
        # coherencia de configuracion tambien se sostiene cuando el
        # origen es una unica lectura de entorno, no un config construido
        # a mano en el test.
        distinctive_env = {
            "PHOENIX_BYBIT_DEMO_API_KEY": "ENV-KEY-ZZZ",
            "PHOENIX_BYBIT_DEMO_API_SECRET": "ENV-SECRET-YYY",
            "PHOENIX_BYBIT_RECV_WINDOW_MS": "7777",
            "PHOENIX_HTTP_TIMEOUT_SECONDS": "23",
        }
        reader = bootstrap_bybit_demo_exchange_state_reader_from_env(environ=distinctive_env)
        p = _config_fingerprint(reader._positions_reader)
        o = _config_fingerprint(reader._open_orders_reader)
        w = _config_fingerprint(reader._wallet_balance_reader)
        assert p == o == w
        assert p["api_key"] == "ENV-KEY-ZZZ"
        assert p["api_secret"] == "ENV-SECRET-YYY"
        assert p["recv_window_ms"] == 7777
        assert p["timeout_seconds"] == 23
