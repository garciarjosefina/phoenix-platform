from collections.abc import Mapping

from execution_gateway.http_get_transport import HttpGetTransport


class HttpGetRequestExecutor:
    def __init__(
        self,
        transport: HttpGetTransport,
        timeout_seconds: float,
    ) -> None:
        if not isinstance(transport, HttpGetTransport):
            raise TypeError(
                f"transport must be compatible with HttpGetTransport, got: {type(transport).__name__}"
            )
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise TypeError(
                f"timeout_seconds must be int or float, got: {type(timeout_seconds).__name__}"
            )
        if timeout_seconds <= 0:
            raise ValueError(f"timeout_seconds must be > 0, got: {timeout_seconds}")

        self._transport = transport
        self._timeout_seconds = timeout_seconds

    def execute(self, *, url: str, headers: Mapping[str, str]) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")
        if not isinstance(headers, Mapping):
            raise TypeError(f"headers must be a Mapping, got: {type(headers).__name__}")

        return self._transport.get(
            url=url,
            headers=headers,
            timeout_seconds=self._timeout_seconds,
        )
