from execution_gateway.bybit_authenticator import BybitAuthenticator
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.bybit_request_builder import BybitRequestBuilder
from execution_gateway.json_serializer import JsonSerializer


def create_bybit_request_builder(
    *,
    serializer: JsonSerializer,
    authenticator: BybitAuthenticator,
    header_builder: BybitHeaderBuilder,
) -> BybitRequestBuilder:
    if not isinstance(serializer, JsonSerializer):
        raise TypeError(
            f"serializer must be compatible with JsonSerializer, got: {type(serializer).__name__}"
        )
    if not isinstance(authenticator, BybitAuthenticator):
        raise TypeError(
            f"authenticator must be compatible with BybitAuthenticator, got: {type(authenticator).__name__}"
        )
    if not isinstance(header_builder, BybitHeaderBuilder):
        raise TypeError(
            f"header_builder must be BybitHeaderBuilder, got: {type(header_builder).__name__}"
        )
    return BybitRequestBuilder(
        serializer=serializer,
        authenticator=authenticator,
        header_builder=header_builder,
    )
