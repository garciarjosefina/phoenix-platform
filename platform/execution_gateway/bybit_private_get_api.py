from execution_gateway.bybit_private_get_request_sender import BybitPrivateGetRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"


class BybitPrivateGetApi:
    def __init__(
        self,
        sender: BybitPrivateGetRequestSender,
        response_parser: BybitResponseParser,
    ) -> None:
        if not isinstance(sender, BybitPrivateGetRequestSender):
            raise TypeError(
                f"sender must be BybitPrivateGetRequestSender, got: {type(sender).__name__}"
            )
        if not isinstance(response_parser, BybitResponseParser):
            raise TypeError(
                f"response_parser must be BybitResponseParser, got: {type(response_parser).__name__}"
            )
        self._sender = sender
        self._response_parser = response_parser

    def request(self, *, url: str, query_string: str) -> BybitResponse:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")
        if not isinstance(query_string, str):
            raise TypeError(f"query_string must be str, got: {type(query_string).__name__}")

        try:
            response_text = self._sender.send(url=url, query_string=query_string)
        except UnicodeDecodeError as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error

        return self._response_parser.parse(response_text=response_text)
