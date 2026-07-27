from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_url_builder import BybitUrlBuilder

_BYBIT_DEMO_BASE_URL = "https://api-demo.bybit.com"


def create_bybit_demo_execution_gateway(
    *,
    private_api: BybitPrivateApi,
) -> BybitExecutionGateway:
    if not isinstance(private_api, BybitPrivateApi):
        raise TypeError(
            f"private_api must be BybitPrivateApi, got: {type(private_api).__name__}"
        )
    url_builder = BybitUrlBuilder(base_url=_BYBIT_DEMO_BASE_URL)
    endpoint_executor = BybitEndpointExecutor(
        url_builder=url_builder,
        private_api=private_api,
    )
    client = create_bybit_demo_client(endpoint_executor=endpoint_executor)
    return BybitExecutionGateway(client=client)
