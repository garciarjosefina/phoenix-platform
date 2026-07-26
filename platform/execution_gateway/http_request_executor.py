from execution_gateway.http_request import HttpRequest
from execution_gateway.http_transport import HttpTransport


class HttpRequestExecutor:
    def __init__(
        self,
        transport: HttpTransport,
        timeout_seconds: float,
    ) -> None:
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

        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def execute(self, *, request: HttpRequest) -> str:
        if not isinstance(request, HttpRequest):
            raise TypeError(
                f"request must be HttpRequest, got: {type(request).__name__}"
            )
        return self._transport.post(
            url=request.url,
            headers=request.headers,
            body=request.body,
            timeout_seconds=self._timeout_seconds,
        )
