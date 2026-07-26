from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_response_interpreter import BybitCreateOrderResponseInterpreter
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT


class BybitCreateOrderOperation:
    def __init__(
        self,
        payload_builder: BybitCreateOrderPayloadBuilder,
        endpoint_executor: BybitEndpointExecutor,
        response_interpreter: BybitCreateOrderResponseInterpreter,
    ) -> None:
        if not isinstance(payload_builder, BybitCreateOrderPayloadBuilder):
            raise TypeError(
                f"payload_builder must be BybitCreateOrderPayloadBuilder, got: {type(payload_builder).__name__}"
            )
        if not isinstance(endpoint_executor, BybitEndpointExecutor):
            raise TypeError(
                f"endpoint_executor must be BybitEndpointExecutor, got: {type(endpoint_executor).__name__}"
            )
        if not isinstance(response_interpreter, BybitCreateOrderResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitCreateOrderResponseInterpreter, got: {type(response_interpreter).__name__}"
            )
        self._payload_builder = payload_builder
        self._endpoint_executor = endpoint_executor
        self._response_interpreter = response_interpreter

    def execute(self, *, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        if not isinstance(request, BybitCreateOrderRequest):
            raise TypeError(
                f"request must be BybitCreateOrderRequest, got: {type(request).__name__}"
            )
        payload = self._payload_builder.build(request=request)
        response = self._endpoint_executor.execute(
            endpoint=BYBIT_CREATE_ORDER_ENDPOINT,
            payload=payload,
        )
        return self._response_interpreter.interpret(response=response)
