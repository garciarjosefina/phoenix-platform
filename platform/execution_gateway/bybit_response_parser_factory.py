from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.json_serializer import JsonSerializer


def create_bybit_response_parser(
    *,
    serializer: JsonSerializer,
) -> BybitResponseParser:
    if not isinstance(serializer, JsonSerializer):
        raise TypeError(
            f"serializer must be compatible with JsonSerializer, got: {type(serializer).__name__}"
        )
    return BybitResponseParser(serializer=serializer)
