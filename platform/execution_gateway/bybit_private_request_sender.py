from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.http_request_executor import HttpRequestExecutor


class BybitPrivateRequestSender:
    def __init__(
        self,
        request_builder: BybitRequestBuilder,
        request_executor: HttpRequestExecutor,
    ) -> None:
        if not isinstance(request_builder, BybitRequestBuilder):
            raise TypeError(
                f"request_builder must be BybitRequestBuilder, got: {type(request_builder).__name__}"
            )
        if not isinstance(request_executor, HttpRequestExecutor):
            raise TypeError(
                f"request_executor must be HttpRequestExecutor, got: {type(request_executor).__name__}"
            )
        self._request_builder = request_builder
        self._request_executor = request_executor

    def send(self, *, url: str, payload: object) -> str:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        request = self._request_builder.build(url=url, payload=payload)
        return self._request_executor.execute(request=request)
