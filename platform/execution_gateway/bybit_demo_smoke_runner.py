from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_demo_connectivity_smoke_test import smoke_test_bybit_demo_connection
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.environment_configuration_error import EnvironmentConfigurationError
from execution_gateway.smoke_test_result import SmokeTestResult

_SUCCESS_HEADER = "PHOENIX_BYBIT_DEMO_SMOKE_TEST_SUCCESS"
_FAILURE_HEADER = "PHOENIX_BYBIT_DEMO_SMOKE_TEST_FAILURE"
_NONE_LITERAL = "NONE"

_API_FAILURE_MESSAGE = "Bybit authentication or API validation failure"
# Los tres errores de transporte relevantes heredan de OSError en la
# biblioteca estándar; capturar OSError los cubre a los tres sin agregar
# ningún import de bajo nivel a este módulo.
_TRANSPORT_FAILURE_MESSAGE = "Remote connectivity or HTTP failure"
_UNEXPECTED_FAILURE_MESSAGE = "Unexpected smoke test failure"
_NOT_SUCCESSFUL_MESSAGE = "smoke test reported success=False"


def _print_success(result: SmokeTestResult) -> None:
    print(_SUCCESS_HEADER)
    print(f"success={result.success}")
    print(f"endpoint={result.endpoint}")
    print(f"environment={result.environment}")
    print(f"server_time={_NONE_LITERAL if result.server_time is None else result.server_time}")
    print(f"account_type={_NONE_LITERAL if result.account_type is None else result.account_type}")


def _print_failure(*, error_type: str, error_message: str) -> None:
    print(_FAILURE_HEADER)
    print(f"error_type={error_type}")
    print(f"error_message={error_message}")


def main() -> int:
    try:
        result = smoke_test_bybit_demo_connection(environ=None)
    except EnvironmentConfigurationError as error:
        _print_failure(error_type=type(error).__name__, error_message=str(error))
        return 1
    except (TypeError, ValueError) as error:
        _print_failure(error_type=type(error).__name__, error_message=str(error))
        return 1
    except BybitApiError as error:
        _print_failure(error_type=type(error).__name__, error_message=_API_FAILURE_MESSAGE)
        return 1
    except BybitResponseProcessingError as error:
        _print_failure(error_type=type(error).__name__, error_message=str(error))
        return 1
    except OSError as error:
        _print_failure(error_type=type(error).__name__, error_message=_TRANSPORT_FAILURE_MESSAGE)
        return 1
    except Exception as error:
        _print_failure(error_type=type(error).__name__, error_message=_UNEXPECTED_FAILURE_MESSAGE)
        return 1

    if not result.success:
        _print_failure(error_type="SmokeTestResult", error_message=_NOT_SUCCESSFUL_MESSAGE)
        return 1

    _print_success(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
