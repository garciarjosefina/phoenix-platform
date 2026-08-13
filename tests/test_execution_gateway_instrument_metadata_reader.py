from decimal import Decimal

import execution_gateway
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata
from execution_gateway.instrument_metadata_reader import InstrumentMetadataReader


class _ValidReader:
    def __init__(self, result: ExecutionInstrumentMetadata):
        self._result = result
        self.calls = 0

    def query_instrument_metadata(self, *, symbol: str) -> ExecutionInstrumentMetadata:
        self.calls += 1
        return self._result


class _NoQueryInstrumentMetadata:
    def execute(self):
        ...


_METADATA = ExecutionInstrumentMetadata(
    symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
    instrument_status="Trading", contract_type="LinearPerpetual",
    tick_size=Decimal("0.1"), min_price=Decimal("0.1"), max_price=Decimal("100"),
    qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
    server_time_ms=1,
)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.instrument_metadata_reader import InstrumentMetadataReader as R
        assert R is InstrumentMetadataReader

    def test_public_import(self):
        assert hasattr(execution_gateway, "InstrumentMetadataReader")
        assert execution_gateway.InstrumentMetadataReader is InstrumentMetadataReader

    def test_in_all(self):
        assert "InstrumentMetadataReader" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidReader(_METADATA), InstrumentMetadataReader)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoQueryInstrumentMetadata(), InstrumentMetadataReader)

    def test_returns_execution_instrument_metadata(self):
        reader = _ValidReader(_METADATA)
        assert reader.query_instrument_metadata(symbol="BTCUSDT") is _METADATA

    def test_positions_reader_is_a_different_protocol(self):
        from execution_gateway.positions_reader import PositionsReader
        assert InstrumentMetadataReader is not PositionsReader

    def test_open_orders_reader_is_a_different_protocol(self):
        from execution_gateway.open_orders_reader import OpenOrdersReader
        assert InstrumentMetadataReader is not OpenOrdersReader

    def test_wallet_balance_reader_is_a_different_protocol(self):
        from execution_gateway.wallet_balance_reader import WalletBalanceReader
        assert InstrumentMetadataReader is not WalletBalanceReader

    def test_execution_gateway_protocol_is_a_different_protocol(self):
        from execution_gateway.gateway import ExecutionGateway
        assert InstrumentMetadataReader is not ExecutionGateway

    def test_instrument_metadata_reader_has_no_execute_method_requirement(self):
        assert not hasattr(InstrumentMetadataReader, "execute")

    def test_instrument_metadata_reader_has_no_query_positions_requirement(self):
        assert not hasattr(InstrumentMetadataReader, "query_positions")

    def test_instrument_metadata_reader_has_no_query_wallet_balance_requirement(self):
        assert not hasattr(InstrumentMetadataReader, "query_wallet_balance")
