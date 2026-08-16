import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot, ObservationWindow
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot
from execution_gateway.positions_contracts import PositionsSnapshot
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


def _positions(*, server_time_ms=1000):
    return PositionsSnapshot(positions=(), server_time_ms=server_time_ms)


def _open_orders(*, server_time_ms=1000):
    return OpenOrdersSnapshot(orders=(), server_time_ms=server_time_ms)


def _wallet_balance(*, server_time_ms=1000):
    return WalletBalanceSnapshot(
        total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
        total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
        total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=server_time_ms,
    )


def _window(**overrides):
    defaults = dict(earliest_remote_time_ms=1000, latest_remote_time_ms=1000, remote_time_span_ms=0)
    defaults.update(overrides)
    return ObservationWindow(**defaults)


def _snapshot(*, times=(1000, 1000, 1000), window=None, **overrides):
    p_time, o_time, w_time = times
    defaults = dict(
        positions=_positions(server_time_ms=p_time),
        open_orders=_open_orders(server_time_ms=o_time),
        wallet_balance=_wallet_balance(server_time_ms=w_time),
        observation_window=window if window is not None else ObservationWindow(
            earliest_remote_time_ms=min(times),
            latest_remote_time_ms=max(times),
            remote_time_span_ms=max(times) - min(times),
        ),
    )
    defaults.update(overrides)
    return ExchangeStateSnapshot(**defaults)


class TestImport:
    def test_exchange_state_snapshot_importable_from_package(self):
        assert hasattr(execution_gateway, "ExchangeStateSnapshot")
        assert execution_gateway.ExchangeStateSnapshot is ExchangeStateSnapshot

    def test_exchange_state_snapshot_in_all(self):
        assert "ExchangeStateSnapshot" in execution_gateway.__all__

    def test_observation_window_importable_from_package(self):
        assert hasattr(execution_gateway, "ObservationWindow")
        assert execution_gateway.ObservationWindow is ObservationWindow

    def test_observation_window_in_all(self):
        assert "ObservationWindow" in execution_gateway.__all__


class TestObservationWindowContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ObservationWindow)
        assert ObservationWindow.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ObservationWindow)]
        assert names == ["earliest_remote_time_ms", "latest_remote_time_ms", "remote_time_span_ms"]

    def test_cannot_reassign_field(self):
        window = _window()
        with pytest.raises(Exception):
            window.earliest_remote_time_ms = 0

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _window(foo=1)

    # ── tipos y finitud ──────────────────────────────────────────────────

    def test_earliest_must_be_int(self):
        with pytest.raises(TypeError, match="earliest_remote_time_ms must be int"):
            _window(earliest_remote_time_ms=1.5, latest_remote_time_ms=1.5, remote_time_span_ms=0)

    def test_earliest_rejects_bool(self):
        with pytest.raises(TypeError, match="earliest_remote_time_ms must be int"):
            _window(earliest_remote_time_ms=True, latest_remote_time_ms=True, remote_time_span_ms=0)

    def test_earliest_rejects_negative(self):
        with pytest.raises(ValueError, match="earliest_remote_time_ms must be >= 0"):
            _window(earliest_remote_time_ms=-1, latest_remote_time_ms=100, remote_time_span_ms=101)

    def test_latest_must_be_int(self):
        with pytest.raises(TypeError, match="latest_remote_time_ms must be int"):
            _window(latest_remote_time_ms=1.5)

    def test_latest_rejects_negative(self):
        with pytest.raises(ValueError, match="latest_remote_time_ms must be >= 0"):
            _window(earliest_remote_time_ms=0, latest_remote_time_ms=-1, remote_time_span_ms=0)

    def test_span_must_be_int(self):
        with pytest.raises(TypeError, match="remote_time_span_ms must be int"):
            _window(remote_time_span_ms=1.5)

    def test_span_rejects_negative(self):
        with pytest.raises(ValueError, match="remote_time_span_ms must be >= 0"):
            _window(earliest_remote_time_ms=0, latest_remote_time_ms=0, remote_time_span_ms=-1)

    # ── invariantes estructurales ────────────────────────────────────────

    def test_latest_must_be_greater_or_equal_than_earliest(self):
        with pytest.raises(ValueError, match="latest_remote_time_ms must be >= earliest_remote_time_ms"):
            _window(earliest_remote_time_ms=200, latest_remote_time_ms=100, remote_time_span_ms=0)

    def test_span_must_equal_latest_minus_earliest(self):
        with pytest.raises(ValueError, match="remote_time_span_ms must equal"):
            _window(earliest_remote_time_ms=100, latest_remote_time_ms=300, remote_time_span_ms=999)

    def test_all_equal_span_zero_is_valid(self):
        window = _window(earliest_remote_time_ms=5000, latest_remote_time_ms=5000, remote_time_span_ms=0)
        assert window.remote_time_span_ms == 0

    def test_zero_timestamps_valid(self):
        window = _window(earliest_remote_time_ms=0, latest_remote_time_ms=0, remote_time_span_ms=0)
        assert window.earliest_remote_time_ms == 0

    def test_large_timestamps_valid(self):
        window = _window(
            earliest_remote_time_ms=1_900_000_000_000,
            latest_remote_time_ms=1_900_000_000_500,
            remote_time_span_ms=500,
        )
        assert window.remote_time_span_ms == 500

    def test_typical_drift_span_computed_correctly(self):
        window = _window(earliest_remote_time_ms=1000, latest_remote_time_ms=1200, remote_time_span_ms=200)
        assert window.remote_time_span_ms == 200

    def test_repr_does_not_crash(self):
        assert "1000" in repr(_window())

    def test_equality_by_value(self):
        assert _window() == _window()


class TestExchangeStateSnapshotContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExchangeStateSnapshot)
        assert ExchangeStateSnapshot.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExchangeStateSnapshot)]
        assert names == ["positions", "open_orders", "wallet_balance", "observation_window"]

    def test_cannot_reassign_field(self):
        snap = _snapshot()
        with pytest.raises(Exception):
            snap.positions = _positions()

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _snapshot(foo=1)

    def test_no_instrument_metadata_field(self):
        # Decisión explícita del Hito 3.74: ExchangeStateSnapshot NO incluye
        # Instrument Metadata (primitiva por-símbolo, no account-wide).
        names = {f.name for f in dataclasses.fields(ExchangeStateSnapshot)}
        assert "instrument_metadata" not in names
        assert "metadata" not in names

    def test_no_top_level_server_time_field(self):
        # Deliberado: un único server_time_ms "resumen" sugeriría
        # falsamente un instante atómico. Sólo observation_window expone
        # temporalidad.
        names = {f.name for f in dataclasses.fields(ExchangeStateSnapshot)}
        assert "server_time_ms" not in names

    # ── tipos ────────────────────────────────────────────────────────────

    def test_positions_must_be_positions_snapshot(self):
        with pytest.raises(TypeError, match="positions must be PositionsSnapshot"):
            _snapshot(positions=object())

    def test_open_orders_must_be_open_orders_snapshot(self):
        with pytest.raises(TypeError, match="open_orders must be OpenOrdersSnapshot"):
            _snapshot(open_orders=object())

    def test_wallet_balance_must_be_wallet_balance_snapshot(self):
        with pytest.raises(TypeError, match="wallet_balance must be WalletBalanceSnapshot"):
            _snapshot(wallet_balance=object())

    def test_observation_window_must_be_observation_window(self):
        with pytest.raises(TypeError, match="observation_window must be ObservationWindow"):
            _snapshot(window=object())

    def test_all_fields_required_no_defaults(self):
        with pytest.raises(TypeError):
            ExchangeStateSnapshot(positions=_positions())

    # ── consistencia cruzada con observation_window ─────────────────────

    def test_valid_construction_succeeds(self):
        snap = _snapshot(times=(1000, 1200, 1100))
        assert snap.observation_window.earliest_remote_time_ms == 1000
        assert snap.observation_window.latest_remote_time_ms == 1200
        assert snap.observation_window.remote_time_span_ms == 200

    def test_mismatched_earliest_rejected(self):
        bad_window = _window(earliest_remote_time_ms=1, latest_remote_time_ms=1200, remote_time_span_ms=1199)
        with pytest.raises(ValueError, match="earliest_remote_time_ms does not match"):
            _snapshot(times=(1000, 1200, 1100), window=bad_window)

    def test_mismatched_latest_rejected(self):
        bad_window = _window(
            earliest_remote_time_ms=1000, latest_remote_time_ms=9999, remote_time_span_ms=8999
        )
        with pytest.raises(ValueError, match="latest_remote_time_ms does not match"):
            _snapshot(times=(1000, 1200, 1100), window=bad_window)

    def test_window_from_different_round_rejected(self):
        # "Mezclar round 1 con round 2": una ObservationWindow calculada
        # para OTRO conjunto de timestamps no debe colar silenciosamente.
        other_round_window = _window(
            earliest_remote_time_ms=50, latest_remote_time_ms=60, remote_time_span_ms=10
        )
        with pytest.raises(ValueError):
            _snapshot(times=(1000, 1200, 1100), window=other_round_window)

    def test_all_equal_timestamps_valid(self):
        snap = _snapshot(times=(5000, 5000, 5000))
        assert snap.observation_window.remote_time_span_ms == 0

    def test_order_of_extremes_independent_of_read_order(self):
        # positions tiene el timestamp MAS RECIENTE, open_orders el MAS
        # ANTIGUO -- earliest/latest deben seguir siendo correctos aunque
        # no coincidan con el orden de lectura positions->orders->wallet.
        snap = _snapshot(times=(1200, 1000, 1100))
        assert snap.observation_window.earliest_remote_time_ms == 1000
        assert snap.observation_window.latest_remote_time_ms == 1200

    # ── superficie / equality ────────────────────────────────────────────

    def test_repr_does_not_crash(self):
        repr(_snapshot())

    def test_equality_by_value(self):
        assert _snapshot() == _snapshot()

    def test_no_bybit_types_in_public_attributes(self):
        snap = _snapshot()
        public = {k for k in vars(snap) if not k.startswith("_")}
        assert public == {"positions", "open_orders", "wallet_balance", "observation_window"}


class TestPurityByAst:
    _FORBIDDEN_SUBSTRINGS = ("bybit", "urllib", "http", "requests", "socket")

    def _module_imports(self, module) -> list[str]:
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(module))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def test_contracts_module_has_no_forbidden_imports(self):
        import execution_gateway.exchange_state_contracts as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_contracts_module_imports_only_dataclasses_and_sibling_contracts(self):
        import execution_gateway.exchange_state_contracts as module
        imports = self._module_imports(module)
        assert set(imports) == {
            "dataclasses",
            "execution_gateway.open_orders_contracts",
            "execution_gateway.positions_contracts",
            "execution_gateway.wallet_balance_contracts",
        }

    def test_reader_protocol_module_has_no_forbidden_imports(self):
        import execution_gateway.exchange_state_reader as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_reader_protocol_module_only_imports_typing_and_own_contract(self):
        import execution_gateway.exchange_state_reader as module
        imports = self._module_imports(module)
        assert set(imports) == {"typing", "execution_gateway.exchange_state_contracts"}

    def test_composite_reader_module_has_no_bybit_imports(self):
        # El agregador depende únicamente de los tres Ports (Protocols) --
        # nunca de un adapter Bybit concreto.
        import execution_gateway.composite_exchange_state_reader as module
        imports = self._module_imports(module)
        violations = [i for i in imports if "bybit" in i.lower()]
        assert violations == []
