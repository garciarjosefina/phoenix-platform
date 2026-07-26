from execution_gateway.bybit_authenticator import BybitAuthenticator
from execution_gateway.bybit_header_builder import BybitHeaderBuilder
from execution_gateway.http_request import HttpRequest
from execution_gateway.json_serializer import JsonSerializer


class BybitRequestBuilder:
    def __init__(
        self,
        serializer: JsonSerializer,
        authenticator: BybitAuthenticator,
        header_builder: BybitHeaderBuilder,
    ) -> None:
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
        self._serializer = serializer
        self._authenticator = authenticator
        self._header_builder = header_builder

    def build(self, *, url: str, payload: object) -> HttpRequest:
        body = self._serializer.dumps(payload)
        authentication = self._authenticator.authenticate(body=body)
        headers = self._header_builder.build(authentication=authentication)
        return HttpRequest(url=url, headers=headers, body=body)
