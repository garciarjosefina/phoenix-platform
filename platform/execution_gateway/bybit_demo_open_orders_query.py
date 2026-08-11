from collections.abc import Mapping

from execution_gateway.bybit_demo_open_orders_reader_env_bootstrap import (
    bootstrap_bybit_demo_open_orders_reader_from_env,
)
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot


def query_bybit_demo_open_orders(
    *,
    environ: Mapping[str, str] | None = None,
) -> OpenOrdersSnapshot:
    reader = bootstrap_bybit_demo_open_orders_reader_from_env(environ=environ)
    return reader.query_open_orders()
