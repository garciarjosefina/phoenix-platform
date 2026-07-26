from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_url_builder import BybitUrlBuilder


class BybitEndpointExecutor:
    def __init__(
        self,
        url_builder: BybitUrlBuilder,
        private_api: BybitPrivateApi,
    ) -> None:
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(private_api, BybitPrivateApi):
            raise TypeError(
                f"private_api must be BybitPrivateApi, got: {type(private_api).__name__}"
            )
        self._url_builder = url_builder
        self._private_api = private_api

    def execute(
        self,
        *,
        endpoint: BybitEndpoint,
        payload: object,
    ) -> BybitResponse:
        if not isinstance(endpoint, BybitEndpoint):
            raise TypeError(
                f"endpoint must be BybitEndpoint, got: {type(endpoint).__name__}"
            )
        url = self._url_builder.build(endpoint=endpoint)
        return self._private_api.request(url=url, payload=payload)
