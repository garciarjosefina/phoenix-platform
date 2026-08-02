from decimal import Decimal

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError

_SIDE_TO_BYBIT = {"buy": "Buy", "sell": "Sell"}
_ORDER_TYPE_TO_BYBIT = {"market": "Market", "limit": "Limit"}
_DEFAULT_TIME_IN_FORCE = "GTC"


class BybitExecutionGateway:
    def __init__(self, client: BybitDemoClient) -> None:
        if not isinstance(client, BybitDemoClient):
            raise TypeError(
                f"client must be compatible with BybitDemoClient, got: {type(client).__name__}"
            )
        self._client = client

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        bybit_request = self._to_bybit_request(request)
        try:
            bybit_result = self._client.place_order(bybit_request)
        except BybitApiError as error:
            return self._to_rejected_result(request=request, error=error)
        except Exception as error:
            raise ExecutionInfrastructureError(message=str(error)) from error
        return self._to_execution_result(request=request, result=bybit_result)

    def _to_bybit_request(self, request: ExecutionRequest) -> BybitCreateOrderRequest:
        return BybitCreateOrderRequest(
            symbol=request.symbol,
            side=_SIDE_TO_BYBIT[request.side],
            order_type=_ORDER_TYPE_TO_BYBIT[request.order_type],
            quantity=Decimal(str(request.quantity)),
            price=Decimal(str(request.price)) if request.price is not None else None,
            time_in_force=_DEFAULT_TIME_IN_FORCE,
            reduce_only=False,
            order_link_id=request.order_id,
        )

    def _to_execution_result(
        self, *, request: ExecutionRequest, result: BybitCreateOrderResult
    ) -> ExecutionResult:
        return ExecutionResult(
            order_id=request.order_id,
            status="accepted",
            exchange_order_id=result.order_id,
        )

    def _to_rejected_result(
        self, *, request: ExecutionRequest, error: BybitApiError
    ) -> ExecutionResult:
        return ExecutionResult(
            order_id=request.order_id,
            status="rejected",
            error_message=error.ret_msg,
        )
