from typing import Protocol, runtime_checkable

from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderLookupResult


@runtime_checkable
class OrderRealtimeLookupReader(Protocol):
    def lookup_by_execution_order_id(
        self, *, execution_order_id: ExecutionOrderId
    ) -> BybitRealtimeOrderLookupResult | BybitOrderHistoryOrderFound:
        ...
