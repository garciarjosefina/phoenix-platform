from collections.abc import Mapping

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"


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
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        if "orderId" not in result or "orderLinkId" not in result:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        try:
            return BybitCreateOrderResult(
                order_id=result["orderId"],
                order_link_id=result["orderLinkId"],
            )
        except (TypeError, ValueError) as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error
