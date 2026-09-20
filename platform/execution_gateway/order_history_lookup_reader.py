from typing import Protocol, runtime_checkable

from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryLookupResult


@runtime_checkable
class OrderHistoryLookupReader(Protocol):
    def lookup_by_execution_order_id(
        self, *, execution_order_id: ExecutionOrderId
    ) -> BybitOrderHistoryLookupResult:
        ...
