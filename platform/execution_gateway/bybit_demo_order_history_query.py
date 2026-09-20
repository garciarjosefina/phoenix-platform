from collections.abc import Mapping

from execution_gateway.bybit_demo_order_history_lookup_env_bootstrap import (
    bootstrap_bybit_demo_order_history_lookup_from_env,
)
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryLookupResult


def query_bybit_demo_order_history_by_execution_order_id(
    *,
    execution_order_id: ExecutionOrderId,
    environ: Mapping[str, str] | None = None,
) -> BybitOrderHistoryLookupResult:
    reader = bootstrap_bybit_demo_order_history_lookup_from_env(environ=environ)
    return reader.lookup_by_execution_order_id(execution_order_id=execution_order_id)
