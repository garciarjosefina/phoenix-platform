from typing import Protocol, runtime_checkable

from execution_gateway.open_orders_contracts import OpenOrdersSnapshot


@runtime_checkable
class OpenOrdersReader(Protocol):
    def query_open_orders(self) -> OpenOrdersSnapshot:
        ...
