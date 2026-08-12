from decimal import Decimal

import execution_gateway
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot
from execution_gateway.wallet_balance_reader import WalletBalanceReader


class _ValidReader:
    def __init__(self, result: WalletBalanceSnapshot):
        self._result = result
        self.calls = 0

    def query_wallet_balance(self) -> WalletBalanceSnapshot:
        self.calls += 1
        return self._result


class _NoQueryWalletBalance:
    def execute(self):
        ...


_SNAPSHOT = WalletBalanceSnapshot(
    total_equity=Decimal("1"),
    total_wallet_balance=Decimal("1"),
    total_available_balance=Decimal("1"),
    total_initial_margin=Decimal("0"),
    total_maintenance_margin=Decimal("0"),
    currency_balances=(),
    server_time_ms=1,
)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.wallet_balance_reader import WalletBalanceReader as R
        assert R is WalletBalanceReader

    def test_public_import(self):
        assert hasattr(execution_gateway, "WalletBalanceReader")
        assert execution_gateway.WalletBalanceReader is WalletBalanceReader

    def test_in_all(self):
        assert "WalletBalanceReader" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidReader(_SNAPSHOT), WalletBalanceReader)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoQueryWalletBalance(), WalletBalanceReader)

    def test_returns_wallet_balance_snapshot(self):
        reader = _ValidReader(_SNAPSHOT)
        assert reader.query_wallet_balance() is _SNAPSHOT

    def test_positions_reader_is_a_different_protocol(self):
        from execution_gateway.positions_reader import PositionsReader
        assert WalletBalanceReader is not PositionsReader

    def test_open_orders_reader_is_a_different_protocol(self):
        from execution_gateway.open_orders_reader import OpenOrdersReader
        assert WalletBalanceReader is not OpenOrdersReader

    def test_execution_gateway_protocol_is_a_different_protocol(self):
        from execution_gateway.gateway import ExecutionGateway
        assert WalletBalanceReader is not ExecutionGateway

    def test_wallet_balance_reader_has_no_execute_method_requirement(self):
        assert not hasattr(WalletBalanceReader, "execute")

    def test_wallet_balance_reader_has_no_query_positions_requirement(self):
        assert not hasattr(WalletBalanceReader, "query_positions")

    def test_wallet_balance_reader_has_no_query_open_orders_requirement(self):
        assert not hasattr(WalletBalanceReader, "query_open_orders")
