from decimal import Decimal

import execution_gateway
from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot, ObservationWindow
from execution_gateway.exchange_state_reader import ExchangeStateReader
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot
from execution_gateway.positions_contracts import PositionsSnapshot
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


class _ValidReader:
    def __init__(self, result: ExchangeStateSnapshot):
        self._result = result
        self.calls = 0

    def query_exchange_state(self) -> ExchangeStateSnapshot:
        self.calls += 1
        return self._result


class _NoQueryExchangeState:
    def execute(self):
        ...


_SNAPSHOT = ExchangeStateSnapshot(
    positions=PositionsSnapshot(positions=(), server_time_ms=1),
    open_orders=OpenOrdersSnapshot(orders=(), server_time_ms=1),
    wallet_balance=WalletBalanceSnapshot(
        total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
        total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
        total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=1,
    ),
    observation_window=ObservationWindow(
        earliest_remote_time_ms=1, latest_remote_time_ms=1, remote_time_span_ms=0
    ),
)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.exchange_state_reader import ExchangeStateReader as R
        assert R is ExchangeStateReader

    def test_public_import(self):
        assert hasattr(execution_gateway, "ExchangeStateReader")
        assert execution_gateway.ExchangeStateReader is ExchangeStateReader

    def test_in_all(self):
        assert "ExchangeStateReader" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidReader(_SNAPSHOT), ExchangeStateReader)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoQueryExchangeState(), ExchangeStateReader)

    def test_returns_exchange_state_snapshot(self):
        reader = _ValidReader(_SNAPSHOT)
        assert reader.query_exchange_state() is _SNAPSHOT

    def test_positions_reader_is_a_different_protocol(self):
        from execution_gateway.positions_reader import PositionsReader
        assert ExchangeStateReader is not PositionsReader

    def test_open_orders_reader_is_a_different_protocol(self):
        from execution_gateway.open_orders_reader import OpenOrdersReader
        assert ExchangeStateReader is not OpenOrdersReader

    def test_wallet_balance_reader_is_a_different_protocol(self):
        from execution_gateway.wallet_balance_reader import WalletBalanceReader
        assert ExchangeStateReader is not WalletBalanceReader

    def test_instrument_metadata_reader_is_a_different_protocol(self):
        from execution_gateway.instrument_metadata_reader import InstrumentMetadataReader
        assert ExchangeStateReader is not InstrumentMetadataReader

    def test_execution_gateway_protocol_is_a_different_protocol(self):
        from execution_gateway.gateway import ExecutionGateway
        assert ExchangeStateReader is not ExecutionGateway

    def test_exchange_state_reader_has_no_execute_method_requirement(self):
        assert not hasattr(ExchangeStateReader, "execute")

    def test_exchange_state_reader_has_no_query_positions_requirement(self):
        assert not hasattr(ExchangeStateReader, "query_positions")

    def test_exchange_state_reader_has_no_symbol_parameter_requirement(self):
        import inspect
        sig = inspect.signature(ExchangeStateReader.query_exchange_state)
        assert "symbol" not in sig.parameters
