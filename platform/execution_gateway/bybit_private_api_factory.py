from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_private_request_sender import BybitPrivateRequestSender
from execution_gateway.bybit_response_parser import BybitResponseParser


def create_bybit_private_api(
    *,
    sender: BybitPrivateRequestSender,
    response_parser: BybitResponseParser,
) -> BybitPrivateApi:
    if not isinstance(sender, BybitPrivateRequestSender):
        raise TypeError(
            f"sender must be BybitPrivateRequestSender, got: {type(sender).__name__}"
        )
    if not isinstance(response_parser, BybitResponseParser):
        raise TypeError(
            f"response_parser must be BybitResponseParser, got: {type(response_parser).__name__}"
        )
    return BybitPrivateApi(sender=sender, response_parser=response_parser)
