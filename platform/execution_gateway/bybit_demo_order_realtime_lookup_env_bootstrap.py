from collections.abc import Mapping

from execution_gateway.bybit_demo_execution_config_env_loader import (
    load_bybit_demo_execution_config_from_env,
)
from execution_gateway.bybit_order_realtime_lookup import BybitOrderRealtimeLookup
from execution_gateway.configured_bybit_demo_order_realtime_lookup_factory import (
    create_configured_bybit_demo_order_realtime_lookup,
)


def bootstrap_bybit_demo_order_realtime_lookup_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitOrderRealtimeLookup:
    config = load_bybit_demo_execution_config_from_env(environ=environ)
    return create_configured_bybit_demo_order_realtime_lookup(config=config)
