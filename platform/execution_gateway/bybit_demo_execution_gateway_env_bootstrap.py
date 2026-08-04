from collections.abc import Mapping

from execution_gateway.bybit_demo_execution_config_env_loader import (
    load_bybit_demo_execution_config_from_env,
)
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.configured_bybit_demo_execution_gateway_factory import (
    create_configured_bybit_demo_execution_gateway,
)


def bootstrap_bybit_demo_execution_gateway_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitExecutionGateway:
    config = load_bybit_demo_execution_config_from_env(environ=environ)
    return create_configured_bybit_demo_execution_gateway(config=config)
