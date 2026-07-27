from collections.abc import Mapping

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_response import BybitResponse


class BybitCreateOrderResponseInterpreter:
    def interpret(self, *, response: BybitResponse) -> BybitCreateOrderResult:
        if not isinstance(response, BybitResponse):
            raise TypeError(
                f"response must be BybitResponse, got: {type(response).__name__}"
            )

        if response.ret_code != 0:
            raise BybitApiError(
                ret_code=response.ret_code,
                ret_msg=response.ret_msg,
            )

        result = response.result
        if not isinstance(result, Mapping):
            raise TypeError(
                f"result must be a mapping, got: {type(result).__name__}"
            )

        if "orderId" not in result:
            raise ValueError("result is missing required key 'orderId'")

        if "orderLinkId" not in result:
            raise ValueError("result is missing required key 'orderLinkId'")

        order_id = result["orderId"]
        order_link_id = result["orderLinkId"]

        if not isinstance(order_id, str):
            raise TypeError(
                f"orderId must be str, got: {type(order_id).__name__}"
            )

        if not isinstance(order_link_id, str):
            raise TypeError(
                f"orderLinkId must be str, got: {type(order_link_id).__name__}"
            )

        return BybitCreateOrderResult(
            order_id=order_id,
            order_link_id=order_link_id,
        )
