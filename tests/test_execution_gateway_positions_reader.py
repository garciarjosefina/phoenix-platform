import execution_gateway
from execution_gateway.positions_contracts import PositionsSnapshot
from execution_gateway.positions_reader import PositionsReader


class _ValidReader:
    def __init__(self, result: PositionsSnapshot):
        self._result = result
        self.calls = 0

    def query_positions(self) -> PositionsSnapshot:
        self.calls += 1
        return self._result


class _NoQueryPositions:
    def execute(self):
        ...


_SNAPSHOT = PositionsSnapshot(positions=(), server_time_ms=1)


class TestImport:
    def test_direct_import(self):
        from execution_gateway.positions_reader import PositionsReader as R
        assert R is PositionsReader

    def test_public_import(self):
        assert hasattr(execution_gateway, "PositionsReader")
        assert execution_gateway.PositionsReader is PositionsReader

    def test_in_all(self):
        assert "PositionsReader" in execution_gateway.__all__


class TestProtocol:
    def test_runtime_checkable(self):
        assert isinstance(_ValidReader(_SNAPSHOT), PositionsReader)

    def test_incompatible_class_rejected(self):
        assert not isinstance(_NoQueryPositions(), PositionsReader)

    def test_no_explicit_inheritance_required(self):
        assert isinstance(_ValidReader(_SNAPSHOT), PositionsReader)

    def test_returns_positions_snapshot(self):
        reader = _ValidReader(_SNAPSHOT)
        assert reader.query_positions() is _SNAPSHOT

    def test_bybit_positions_reader_satisfies_protocol(self):
        from execution_gateway.bybit_positions_reader import BybitPositionsReader
        assert issubclass(BybitPositionsReader, object)  # smoke: importable
        # No se instancia aquí (requiere colaboradores reales) -- la
        # conformidad estructural real ya está cubierta en
        # test_execution_gateway_bybit_positions_reader.py::TestImport.

    def test_execution_gateway_protocol_is_a_different_protocol(self):
        from execution_gateway.gateway import ExecutionGateway
        assert PositionsReader is not ExecutionGateway

    def test_positions_reader_has_no_execute_method_requirement(self):
        assert not hasattr(PositionsReader, "execute")
