import execution_gateway
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot
from execution_gateway.open_orders_reader import OpenOrdersReader


class _ValidReader:
    def __init__(self, result: OpenOrdersSnapshot):
        self._result = result
        self.calls = 0

    def query_open_orders(self) -> OpenOrdersSnapshot:
        self.calls += 1
        return self._result


class _NoQueryOpenOrders:
    def execute(self):
        ...


_SNAPSHOT = OpenOrdersSnapshot(orders=(), server_time_ms=1)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.open_orders_reader import OpenOrdersReader as R
        assert R is OpenOrdersReader

    def test_public_import(self):
        assert hasattr(execution_gateway, "OpenOrdersReader")
        assert execution_gateway.OpenOrdersReader is OpenOrdersReader

    def test_in_all(self):
        assert "OpenOrdersReader" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidReader(_SNAPSHOT), OpenOrdersReader)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoQueryOpenOrders(), OpenOrdersReader)

    def test_returns_open_orders_snapshot(self):
        reader = _ValidReader(_SNAPSHOT)
        assert reader.query_open_orders() is _SNAPSHOT

    def test_positions_reader_is_a_different_protocol(self):
        from execution_gateway.positions_reader import PositionsReader
        assert OpenOrdersReader is not PositionsReader

    def test_execution_gateway_protocol_is_a_different_protocol(self):
        from execution_gateway.gateway import ExecutionGateway
        assert OpenOrdersReader is not ExecutionGateway

    def test_open_orders_reader_has_no_execute_method_requirement(self):
        assert not hasattr(OpenOrdersReader, "execute")

    def test_open_orders_reader_has_no_query_positions_requirement(self):
        assert not hasattr(OpenOrdersReader, "query_positions")
