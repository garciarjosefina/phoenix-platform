from collections.abc import Mapping

from execution_gateway.bybit_demo_exchange_state_reader_env_bootstrap import (
    bootstrap_bybit_demo_exchange_state_reader_from_env,
)
from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot


def query_bybit_demo_exchange_state(
    *,
    environ: Mapping[str, str] | None = None,
) -> ExchangeStateSnapshot:
    reader = bootstrap_bybit_demo_exchange_state_reader_from_env(environ=environ)
    return reader.query_exchange_state()
