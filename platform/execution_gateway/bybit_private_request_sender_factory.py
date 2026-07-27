from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.http_request_executor import HttpRequestExecutor


def create_bybit_private_request_sender(
    *,
    request_builder: BybitRequestBuilder,
    request_executor: HttpRequestExecutor,
) -> BybitPrivateRequestSender:
    if not isinstance(request_builder, BybitRequestBuilder):
        raise TypeError(
            f"request_builder must be BybitRequestBuilder, got: {type(request_builder).__name__}"
        )
    if not isinstance(request_executor, HttpRequestExecutor):
        raise TypeError(
            f"request_executor must be HttpRequestExecutor, got: {type(request_executor).__name__}"
        )
    return BybitPrivateRequestSender(
        request_builder=request_builder,
        request_executor=request_executor,
    )
