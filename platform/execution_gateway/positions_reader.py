from typing import Protocol, runtime_checkable

from execution_gateway.positions_contracts import PositionsSnapshot


@runtime_checkable
class PositionsReader(Protocol):
    def query_positions(self) -> PositionsSnapshot:
        ...
