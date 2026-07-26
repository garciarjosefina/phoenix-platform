from execution_gateway.bybit_response import BybitResponse
from execution_gateway.json_serializer import JsonSerializer


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
        data = self._serializer.loads(response_text)
        if not isinstance(data, dict):
            raise TypeError(
                f"response root must be dict, got: {type(data).__name__}"
            )
        return BybitResponse(
            ret_code=data["retCode"],
            ret_msg=data["retMsg"],
            result=data["result"],
            ret_ext_info=data["retExtInfo"],
            time_ms=data["time"],
        )
