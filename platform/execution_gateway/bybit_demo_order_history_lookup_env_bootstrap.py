from collections.abc import Mapping

from execution_gateway.bybit_demo_execution_config_env_loader import (
    load_bybit_demo_execution_config_from_env,
)
from execution_gateway.bybit_order_history_lookup import BybitOrderHistoryLookup
from execution_gateway.configured_bybit_demo_order_history_lookup_factory import (
    create_configured_bybit_demo_order_history_lookup,
)


def bootstrap_bybit_demo_order_history_lookup_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitOrderHistoryLookup:
    config = load_bybit_demo_execution_config_from_env(environ=environ)
    return create_configured_bybit_demo_order_history_lookup(config=config)
