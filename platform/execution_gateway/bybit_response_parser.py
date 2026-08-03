from json import JSONDecodeError

from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.json_serializer import JsonSerializer

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"


class BybitResponseParser:
    def __init__(self, serializer: JsonSerializer) -> None:
        if not isinstance(serializer, JsonSerializer):
            raise TypeError(
                f"serializer must be compatible with JsonSerializer, got: {type(serializer).__name__}"
            )
        self._serializer = serializer

    def parse(self, *, response_text: str) -> BybitResponse:
        if not isinstance(response_text, str):
            raise TypeError(
                f"response_text must be str, got: {type(response_text).__name__}"
            )

        try:
            data = self._serializer.loads(response_text)
        except JSONDecodeError as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error

        if not isinstance(data, dict):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        try:
            return BybitResponse(
                ret_code=data["retCode"],
                ret_msg=data["retMsg"],
                result=data["result"],
                ret_ext_info=data["retExtInfo"],
                time_ms=data["time"],
            )
        except (KeyError, TypeError, ValueError) as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error
