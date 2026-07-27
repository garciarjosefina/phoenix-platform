from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
from execution_gateway.bybit_create_order_response_interpreter import BybitCreateOrderResponseInterpreter
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor


def create_bybit_demo_client(
    *,
    endpoint_executor: BybitEndpointExecutor,
) -> BybitDemoClient:
    if not isinstance(endpoint_executor, BybitEndpointExecutor):
        raise TypeError(
            f"endpoint_executor must be BybitEndpointExecutor, got: {type(endpoint_executor).__name__}"
        )
    payload_builder = BybitCreateOrderPayloadBuilder()
    response_interpreter = BybitCreateOrderResponseInterpreter()
    create_order_operation = BybitCreateOrderOperation(
        payload_builder=payload_builder,
        endpoint_executor=endpoint_executor,
        response_interpreter=response_interpreter,
    )
    client = BybitDemoClient(
        create_order_operation=create_order_operation,
    )
    return client
