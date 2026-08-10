from collections.abc import Mapping

from execution_gateway.bybit_demo_positions_reader_env_bootstrap import (
    bootstrap_bybit_demo_positions_reader_from_env,
)
from execution_gateway.positions_contracts import PositionsSnapshot


def query_bybit_demo_positions(
    *,
    environ: Mapping[str, str] | None = None,
) -> PositionsSnapshot:
    reader = bootstrap_bybit_demo_positions_reader_from_env(environ=environ)
    return reader.query_positions()
