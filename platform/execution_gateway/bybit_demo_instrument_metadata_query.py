from collections.abc import Mapping

from execution_gateway.bybit_demo_instrument_metadata_reader_env_bootstrap import (
    bootstrap_bybit_demo_instrument_metadata_reader_from_env,
)
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata


def query_bybit_demo_instrument_metadata(
    *,
    symbol: str,
    environ: Mapping[str, str] | None = None,
) -> ExecutionInstrumentMetadata:
    reader = bootstrap_bybit_demo_instrument_metadata_reader_from_env(environ=environ)
    return reader.query_instrument_metadata(symbol=symbol)
