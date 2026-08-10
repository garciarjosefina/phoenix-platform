from collections.abc import Mapping

from execution_gateway.bybit_demo_execution_config_env_loader import (
    load_bybit_demo_execution_config_from_env,
)
from execution_gateway.bybit_positions_reader import BybitPositionsReader
from execution_gateway.configured_bybit_demo_positions_reader_factory import (
    create_configured_bybit_demo_positions_reader,
)


def bootstrap_bybit_demo_positions_reader_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitPositionsReader:
    config = load_bybit_demo_execution_config_from_env(environ=environ)
    return create_configured_bybit_demo_positions_reader(config=config)
