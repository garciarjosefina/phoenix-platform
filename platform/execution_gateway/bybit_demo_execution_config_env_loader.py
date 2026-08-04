import os
from collections.abc import Mapping

from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError

_API_KEY_VAR = "PHOENIX_BYBIT_DEMO_API_KEY"
_API_SECRET_VAR = "PHOENIX_BYBIT_DEMO_API_SECRET"
_RECV_WINDOW_MS_VAR = "PHOENIX_BYBIT_RECV_WINDOW_MS"
_TIMEOUT_SECONDS_VAR = "PHOENIX_HTTP_TIMEOUT_SECONDS"


def _read_required(source: Mapping[str, str], name: str) -> str:
    if name not in source:
        raise EnvironmentConfigurationError(
            message=f"Missing required environment variable: {name}"
        )
    return source[name]


def _read_int(source: Mapping[str, str], name: str) -> int:
    raw = _read_required(source, name)
    try:
        return int(raw)
    except ValueError as error:
        raise EnvironmentConfigurationError(
            message=f"Invalid integer environment variable: {name}"
        ) from error


def _read_float(source: Mapping[str, str], name: str) -> float:
    raw = _read_required(source, name)
    try:
        return float(raw)
    except ValueError as error:
        raise EnvironmentConfigurationError(
            message=f"Invalid numeric environment variable: {name}"
        ) from error


def load_bybit_demo_execution_config_from_env(
    *,
    environ: Mapping[str, str] | None = None,
) -> BybitDemoExecutionConfig:
    if environ is not None and not isinstance(environ, Mapping):
        raise TypeError(f"environ must be a Mapping, got: {type(environ).__name__}")

    source = os.environ if environ is None else environ

    api_key = _read_required(source, _API_KEY_VAR)
    api_secret = _read_required(source, _API_SECRET_VAR)
    recv_window_ms = _read_int(source, _RECV_WINDOW_MS_VAR)
    timeout_seconds = _read_float(source, _TIMEOUT_SECONDS_VAR)

    return BybitDemoExecutionConfig(
        api_key=api_key,
        api_secret=api_secret,
        recv_window_ms=recv_window_ms,
        timeout_seconds=timeout_seconds,
    )
