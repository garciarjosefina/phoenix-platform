from execution_gateway.http_request_executor import HttpRequestExecutor
from execution_gateway.http_transport import HttpTransport


def create_http_request_executor(
    *,
    transport: HttpTransport,
    timeout_seconds: float,
) -> HttpRequestExecutor:
    if not isinstance(transport, HttpTransport):
        raise TypeError(
            f"transport must be compatible with HttpTransport, got: {type(transport).__name__}"
        )
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
        raise TypeError(
            f"timeout_seconds must be int or float, got: {type(timeout_seconds).__name__}"
        )
    if timeout_seconds <= 0:
        raise ValueError(f"timeout_seconds must be > 0, got: {timeout_seconds}")
    return HttpRequestExecutor(transport=transport, timeout_seconds=timeout_seconds)
