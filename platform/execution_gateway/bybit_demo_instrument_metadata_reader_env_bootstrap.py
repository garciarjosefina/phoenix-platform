import os
from collections.abc import Mapping

from execution_gateway.bybit_instrument_metadata_reader import BybitInstrumentMetadataReader
from execution_gateway.configured_bybit_demo_instrument_metadata_reader_factory import (
    create_configured_bybit_demo_instrument_metadata_reader,
)
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError

# Misma variable que BybitDemoExecutionConfig (bybit_demo_execution_config_env_loader.py)
# -- cero variables PHOENIX_* nuevas. Deliberadamente NO se reutiliza
# load_bybit_demo_execution_config_from_env completo: ese loader exige
# también PHOENIX_BYBIT_DEMO_API_KEY/API_SECRET/RECV_WINDOW_MS, que este
# endpoint público no necesita -- exigirlos habría bloqueado una consulta
# de metadata sin ninguna razón real relacionada con el endpoint en sí.
_TIMEOUT_SECONDS_VAR = "PHOENIX_HTTP_TIMEOUT_SECONDS"


def _load_timeout_seconds_from_env(*, environ: Mapping[str, str] | None) -> float:
    source = os.environ if environ is None else environ
    if _TIMEOUT_SECONDS_VAR not in source:
        raise EnvironmentConfigurationError(
            message=f"Missing required environment variable: {_TIMEOUT_SECONDS_VAR}"
        )
    raw = source[_TIMEOUT_SECONDS_VAR]
    try:
        return float(raw)
    except ValueError as error:
        raise EnvironmentConfigurationError(
            message=f"Invalid numeric environment variable: {_TIMEOUT_SECONDS_VAR}"
        ) from error


def bootstrap_bybit_demo_instrument_metadata_reader_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitInstrumentMetadataReader:
    if environ is not None and not isinstance(environ, Mapping):
        raise TypeError(f"environ must be a Mapping, got: {type(environ).__name__}")

    timeout_seconds = _load_timeout_seconds_from_env(environ=environ)
    return create_configured_bybit_demo_instrument_metadata_reader(timeout_seconds=timeout_seconds)
