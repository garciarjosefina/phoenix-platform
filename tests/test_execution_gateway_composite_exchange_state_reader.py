from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.composite_exchange_state_reader import CompositeExchangeStateReader
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot
from execution_gateway.open_orders_reader import OpenOrdersReader
from execution_gateway.positions_contracts import PositionsSnapshot
from execution_gateway.positions_reader import PositionsReader
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot
from execution_gateway.wallet_balance_reader import WalletBalanceReader


def _positions(server_time_ms=1000):
    return PositionsSnapshot(positions=(), server_time_ms=server_time_ms)


def _open_orders(server_time_ms=1000):
    return OpenOrdersSnapshot(orders=(), server_time_ms=server_time_ms)


def _wallet_balance(server_time_ms=1000):
    return WalletBalanceSnapshot(
        total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
        total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
        total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=server_time_ms,
    )


class _SpyPositionsReader(PositionsReader):
    def __init__(self, *, results=None, exc=None):
        self.calls = 0
        self.call_order_marker = None
        self._results = list(results) if results is not None else None
        self._result = _positions()
        self._exc = exc

    def query_positions(self):
        self.calls += 1
        if self.call_order_marker is not None:
            self.call_order_marker.append("positions")
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


class _SpyOpenOrdersReader(OpenOrdersReader):
    def __init__(self, *, results=None, exc=None):
        self.calls = 0
        self.call_order_marker = None
        self._results = list(results) if results is not None else None
        self._result = _open_orders()
        self._exc = exc

    def query_open_orders(self):
        self.calls += 1
        if self.call_order_marker is not None:
            self.call_order_marker.append("open_orders")
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


class _SpyWalletBalanceReader(WalletBalanceReader):
    def __init__(self, *, results=None, exc=None):
        self.calls = 0
        self.call_order_marker = None
        self._results = list(results) if results is not None else None
        self._result = _wallet_balance()
        self._exc = exc

    def query_wallet_balance(self):
        self.calls += 1
        if self.call_order_marker is not None:
            self.call_order_marker.append("wallet_balance")
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


def _reader(*, positions_reader=None, open_orders_reader=None, wallet_balance_reader=None):
    return CompositeExchangeStateReader(
        positions_reader=positions_reader or _SpyPositionsReader(),
        open_orders_reader=open_orders_reader or _SpyOpenOrdersReader(),
        wallet_balance_reader=wallet_balance_reader or _SpyWalletBalanceReader(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "CompositeExchangeStateReader")
        assert execution_gateway.CompositeExchangeStateReader is CompositeExchangeStateReader

    def test_in_all(self):
        assert "CompositeExchangeStateReader" in execution_gateway.__all__

    def test_satisfies_exchange_state_reader_protocol(self):
        from execution_gateway.exchange_state_reader import ExchangeStateReader
        assert isinstance(_reader(), ExchangeStateReader)


class TestConstruction:
    def test_positions_reader_must_satisfy_protocol(self):
        with pytest.raises(TypeError, match="PositionsReader"):
            CompositeExchangeStateReader(
                positions_reader=object(),
                open_orders_reader=_SpyOpenOrdersReader(),
                wallet_balance_reader=_SpyWalletBalanceReader(),
            )

    def test_open_orders_reader_must_satisfy_protocol(self):
        with pytest.raises(TypeError, match="OpenOrdersReader"):
            CompositeExchangeStateReader(
                positions_reader=_SpyPositionsReader(),
                open_orders_reader=object(),
                wallet_balance_reader=_SpyWalletBalanceReader(),
            )

    def test_wallet_balance_reader_must_satisfy_protocol(self):
        with pytest.raises(TypeError, match="WalletBalanceReader"):
            CompositeExchangeStateReader(
                positions_reader=_SpyPositionsReader(),
                open_orders_reader=_SpyOpenOrdersReader(),
                wallet_balance_reader=object(),
            )


class TestQueryExchangeState:
    def test_returns_exchange_state_snapshot(self):
        from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot
        snapshot = _reader().query_exchange_state()
        assert isinstance(snapshot, ExchangeStateSnapshot)

    def test_sub_snapshots_returned_by_identity(self):
        p, o, w = _positions(), _open_orders(), _wallet_balance()
        positions_reader = _SpyPositionsReader(results=[p])
        open_orders_reader = _SpyOpenOrdersReader(results=[o])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[w])
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.positions is p
        assert snapshot.open_orders is o
        assert snapshot.wallet_balance is w

    def test_no_keyword_only_violation_zero_params(self):
        # query_exchange_state() no toma ningún parámetro -- account-wide,
        # sin symbol, a diferencia de InstrumentMetadataReader.
        import inspect
        sig = inspect.signature(CompositeExchangeStateReader.query_exchange_state)
        assert list(sig.parameters.keys()) == ["self"]


class TestObservationWindowComputation:
    def test_earliest_latest_span_computed_from_remote_timestamps(self):
        positions_reader = _SpyPositionsReader(results=[_positions(server_time_ms=1000)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(server_time_ms=1200)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(server_time_ms=1100)])
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.observation_window.earliest_remote_time_ms == 1000
        assert snapshot.observation_window.latest_remote_time_ms == 1200
        assert snapshot.observation_window.remote_time_span_ms == 200

    def test_extremes_independent_of_which_reader_has_them(self):
        # positions tiene el timestamp MAS RECIENTE (no el primero leído).
        positions_reader = _SpyPositionsReader(results=[_positions(server_time_ms=9000)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(server_time_ms=1000)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(server_time_ms=5000)])
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.observation_window.earliest_remote_time_ms == 1000
        assert snapshot.observation_window.latest_remote_time_ms == 9000
        assert snapshot.observation_window.remote_time_span_ms == 8000

    def test_all_identical_timestamps_span_zero(self):
        positions_reader = _SpyPositionsReader(results=[_positions(server_time_ms=42)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(server_time_ms=42)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(server_time_ms=42)])
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.observation_window.remote_time_span_ms == 0

    def test_zero_timestamps_valid(self):
        positions_reader = _SpyPositionsReader(results=[_positions(server_time_ms=0)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(server_time_ms=0)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(server_time_ms=0)])
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.observation_window.earliest_remote_time_ms == 0

    def test_large_timestamps_preserved(self):
        positions_reader = _SpyPositionsReader(results=[_positions(server_time_ms=1_900_000_000_000)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(server_time_ms=1_900_000_000_500)])
        wallet_balance_reader = _SpyWalletBalanceReader(
            results=[_wallet_balance(server_time_ms=1_900_000_000_250)]
        )
        snapshot = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert snapshot.observation_window.remote_time_span_ms == 500

    def test_timestamps_never_replaced_with_local_clock(self):
        # Sólo código real (sin comentarios) -- el módulo documenta en
        # prosa por qué NO usa un reloj local, lo cual mencionaría esas
        # palabras.
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        code_lines = [
            line for line in inspect.getsource(module).splitlines()
            if not line.strip().startswith("#")
        ]
        code = "\n".join(code_lines)
        assert "time.time" not in code
        assert "datetime" not in code
        assert "import time" not in code


class TestReadOrder:
    def test_positions_then_open_orders_then_wallet_balance(self):
        marker = []
        positions_reader = _SpyPositionsReader()
        open_orders_reader = _SpyOpenOrdersReader()
        wallet_balance_reader = _SpyWalletBalanceReader()
        positions_reader.call_order_marker = marker
        open_orders_reader.call_order_marker = marker
        wallet_balance_reader.call_order_marker = marker
        _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert marker == ["positions", "open_orders", "wallet_balance"]

    def test_order_is_deterministic_across_calls(self):
        marker = []
        positions_reader = _SpyPositionsReader(results=[_positions(), _positions()])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(), _open_orders()])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(), _wallet_balance()])
        positions_reader.call_order_marker = marker
        open_orders_reader.call_order_marker = marker
        wallet_balance_reader.call_order_marker = marker
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        reader.query_exchange_state()
        reader.query_exchange_state()
        assert marker == ["positions", "open_orders", "wallet_balance"] * 2


class TestExactlyOnce:
    def test_each_reader_called_exactly_once_per_round(self):
        positions_reader = _SpyPositionsReader()
        open_orders_reader = _SpyOpenOrdersReader()
        wallet_balance_reader = _SpyWalletBalanceReader()
        _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        ).query_exchange_state()
        assert positions_reader.calls == 1
        assert open_orders_reader.calls == 1
        assert wallet_balance_reader.calls == 1

    def test_no_retry_no_second_call_within_a_round(self):
        # Mismo test que el anterior desde otro ángulo -- explícito por
        # nombre para dejar constancia de la garantía "sin retry oculto".
        positions_reader = _SpyPositionsReader()
        _reader(positions_reader=positions_reader).query_exchange_state()
        assert positions_reader.calls == 1


class TestFailClosedOnPartialFailure:
    """Sección 10/11 del Hito 3.74: si un reader falla, NO se devuelve un
    snapshot parcial, y los readers restantes -- según el orden fijo -- ni
    siquiera se llegan a invocar."""

    def test_positions_failure_prevents_snapshot_and_stops_further_reads(self):
        positions_reader = _SpyPositionsReader(exc=ExecutionInfrastructureError(message="down"))
        open_orders_reader = _SpyOpenOrdersReader()
        wallet_balance_reader = _SpyWalletBalanceReader()
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_exchange_state()
        assert positions_reader.calls == 1
        assert open_orders_reader.calls == 0
        assert wallet_balance_reader.calls == 0

    def test_open_orders_failure_prevents_snapshot_wallet_not_called(self):
        positions_reader = _SpyPositionsReader()
        open_orders_reader = _SpyOpenOrdersReader(exc=ExecutionInfrastructureError(message="down"))
        wallet_balance_reader = _SpyWalletBalanceReader()
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_exchange_state()
        assert positions_reader.calls == 1
        assert open_orders_reader.calls == 1
        assert wallet_balance_reader.calls == 0

    def test_wallet_balance_failure_prevents_snapshot(self):
        wallet_balance_reader = _SpyWalletBalanceReader(exc=ExecutionInfrastructureError(message="down"))
        reader = _reader(wallet_balance_reader=wallet_balance_reader)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_exchange_state()

    def test_original_error_preserved_as_cause_not_applicable_since_not_rewrapped(self):
        # No se re-envuelve: la excepción original se propaga literalmente
        # (identidad), no una nueva excepción con __cause__ apuntando a
        # ella -- verificado explícitamente por identidad.
        original = ExecutionInfrastructureError(message="down")
        positions_reader = _SpyPositionsReader(exc=original)
        reader = _reader(positions_reader=positions_reader)
        try:
            reader.query_exchange_state()
            assert False, "expected ExecutionInfrastructureError"
        except ExecutionInfrastructureError as caught:
            assert caught is original

    def test_no_optional_snapshot_fields_hiding_failure(self):
        # Ningún campo de ExchangeStateSnapshot es Optional -- ver también
        # test_execution_gateway_exchange_state_contracts.py.
        from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot
        import dataclasses
        for field in dataclasses.fields(ExchangeStateSnapshot):
            assert field.default is dataclasses.MISSING, (
                f"{field.name} no debe tener default (Optional oculto)"
            )

    def test_internal_bug_type_error_propagates_unwrapped(self):
        positions_reader = _SpyPositionsReader(exc=TypeError("programming bug"))
        reader = _reader(positions_reader=positions_reader)
        with pytest.raises(TypeError, match="programming bug"):
            reader.query_exchange_state()

    def test_internal_bug_runtime_error_propagates_unwrapped(self):
        open_orders_reader = _SpyOpenOrdersReader(exc=RuntimeError("internal bug"))
        reader = _reader(open_orders_reader=open_orders_reader)
        with pytest.raises(RuntimeError, match="internal bug"):
            reader.query_exchange_state()

    def test_internal_bug_attribute_error_propagates_unwrapped(self):
        wallet_balance_reader = _SpyWalletBalanceReader(exc=AttributeError("bug"))
        reader = _reader(wallet_balance_reader=wallet_balance_reader)
        with pytest.raises(AttributeError, match="bug"):
            reader.query_exchange_state()

    def test_no_catch_all_exception_in_source(self):
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        assert "except Exception" not in inspect.getsource(module)

    def test_ret_msg_never_referenced_in_aggregator_source(self):
        # El agregador no toca el error model en absoluto -- ni siquiera
        # sabe qué es ret_msg (eso vive exclusivamente en los tres readers
        # ya aceptados).
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        assert "ret_msg" not in inspect.getsource(module)


class TestNoCacheAcrossCalls:
    """Lección directa del Hito 3.70, aplicada al agregador desde el primer
    commit: dos rondas consecutivas sobre la MISMA instancia deben producir
    dos rondas reales de los tres readers, nunca el snapshot anterior."""

    def test_each_reader_called_exactly_twice_across_two_rounds(self):
        positions_reader = _SpyPositionsReader(results=[_positions(100), _positions(200)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(100), _open_orders(200)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(100), _wallet_balance(200)])
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        reader.query_exchange_state()
        reader.query_exchange_state()
        assert positions_reader.calls == 2
        assert open_orders_reader.calls == 2
        assert wallet_balance_reader.calls == 2

    def test_two_rounds_produce_distinct_snapshots_by_identity(self):
        positions_reader = _SpyPositionsReader(results=[_positions(100), _positions(200)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(100), _open_orders(200)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(100), _wallet_balance(200)])
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        first = reader.query_exchange_state()
        second = reader.query_exchange_state()
        assert first is not second
        assert first.positions is not second.positions

    def test_second_round_reflects_round_two_state_a_then_b(self):
        positions_reader = _SpyPositionsReader(results=[_positions(1000), _positions(5000)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(1000), _open_orders(5000)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(1000), _wallet_balance(5000)])
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        first = reader.query_exchange_state()
        second = reader.query_exchange_state()
        assert first.observation_window.earliest_remote_time_ms == 1000
        assert second.observation_window.earliest_remote_time_ms == 5000

    def test_second_round_with_smaller_timestamps_never_blends_with_first_round(self):
        # Ronda 1 con timestamps GRANDES, ronda 2 con timestamps MAS
        # PEQUENOS -- si el agregador retuviera cualquier estado de la
        # ronda anterior (p.ej. "el latest mas grande visto hasta ahora"),
        # esta seria la unica forma de detectarlo: un caso donde
        # "mezclar" produciria un valor DISTINTO del que la ronda 2 sola
        # produciria. Un test con timestamps crecientes entre rondas no
        # puede detectar este bug porque el valor "mezclado" coincidiria
        # por accidente con el valor correcto.
        positions_reader = _SpyPositionsReader(results=[_positions(9000), _positions(100)])
        open_orders_reader = _SpyOpenOrdersReader(results=[_open_orders(9000), _open_orders(100)])
        wallet_balance_reader = _SpyWalletBalanceReader(results=[_wallet_balance(9000), _wallet_balance(100)])
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        first = reader.query_exchange_state()
        second = reader.query_exchange_state()
        assert first.observation_window.latest_remote_time_ms == 9000
        assert second.observation_window.latest_remote_time_ms == 100
        assert second.observation_window.earliest_remote_time_ms == 100
        assert second.observation_window.remote_time_span_ms == 0

    def test_reader_instance_has_no_cache_attribute_after_query(self):
        reader = _reader()
        reader.query_exchange_state()
        assert not hasattr(reader, "_cached")
        assert not hasattr(reader, "_cache")
        assert not hasattr(reader, "_last_result")
        assert not hasattr(reader, "_last_snapshot")

    def test_two_independent_reader_instances_do_not_share_state(self):
        reader_a = _reader()
        reader_b = _reader()
        assert reader_a is not reader_b
        assert vars(reader_a).keys() == {
            "_positions_reader", "_open_orders_reader", "_wallet_balance_reader",
        }

    def test_second_round_after_first_failure_still_calls_all_readers_again(self):
        positions_reader = _SpyPositionsReader(exc=ExecutionInfrastructureError(message="down"))
        open_orders_reader = _SpyOpenOrdersReader()
        wallet_balance_reader = _SpyWalletBalanceReader()
        reader = _reader(
            positions_reader=positions_reader,
            open_orders_reader=open_orders_reader,
            wallet_balance_reader=wallet_balance_reader,
        )
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_exchange_state()
        positions_reader._exc = None
        reader.query_exchange_state()
        assert positions_reader.calls == 2
        assert open_orders_reader.calls == 1
        assert wallet_balance_reader.calls == 1


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "cancel" not in src.lower()

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.composite_exchange_state_reader as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")

    def test_does_not_reference_instrument_metadata(self):
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        src = inspect.getsource(module)
        assert "InstrumentMetadata" not in src
        assert "symbol" not in src.lower()

    def test_no_reconciliation_vocabulary_in_source(self):
        import inspect
        import execution_gateway.composite_exchange_state_reader as module
        src = inspect.getsource(module).lower()
        for forbidden in ("reconcil", "expected_state", "orphan", "mismatch", "repair", "desired"):
            assert forbidden not in src
