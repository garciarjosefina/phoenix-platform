from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_parser import BybitResponseParser
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"


class BybitPrivateApi:
    def __init__(
        self,
        sender: BybitPrivateRequestSender,
        response_parser: BybitResponseParser,
    ) -> None:
        if not isinstance(sender, BybitPrivateRequestSender):
            raise TypeError(
                f"sender must be BybitPrivateRequestSender, got: {type(sender).__name__}"
            )
        if not isinstance(response_parser, BybitResponseParser):
            raise TypeError(
                f"response_parser must be BybitResponseParser, got: {type(response_parser).__name__}"
            )
        self._sender = sender
        self._response_parser = response_parser

    def request(self, *, url: str, payload: object) -> BybitResponse:
        if not isinstance(url, str):
            raise TypeError(f"url must be str, got: {type(url).__name__}")
        if not url or url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        try:
            response_text = self._sender.send(url=url, payload=payload)
        except UnicodeDecodeError as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error

        return self._response_parser.parse(response_text=response_text)
