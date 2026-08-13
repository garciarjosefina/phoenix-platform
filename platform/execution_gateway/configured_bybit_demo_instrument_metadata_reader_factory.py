from execution_gateway.bybit_demo_instrument_metadata_reader_factory import (
    create_bybit_demo_instrument_metadata_reader,
)
from execution_gateway.bybit_instrument_metadata_reader import BybitInstrumentMetadataReader
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.bybit_public_get_request_sender import BybitPublicGetRequestSender
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.urllib_get_http_transport import UrllibGetHttpTransport


def create_configured_bybit_demo_instrument_metadata_reader(
    *,
    timeout_seconds: int | float,
) -> BybitInstrumentMetadataReader:
    # Deliberadamente NO recibe BybitDemoExecutionConfig: este endpoint es
    # público (sin autenticación, confirmado contra documentación oficial),
    # así que credenciales/recv_window no aplican -- exigirlos habría
    # representado incorrectamente el requisito real del endpoint. Sólo
    # timeout_seconds, la única dependencia operativa que un GET
    # (autenticado o no) necesita. Ver ADR-002, decisión Public/Private GET
    # (Hito 3.73).
    validated_timeout_seconds = create_http_timeout_seconds(timeout_seconds=timeout_seconds)

    serializer = create_json_serializer()
    response_parser = create_bybit_response_parser(serializer=serializer)

    transport = UrllibGetHttpTransport()
    request_executor = HttpGetRequestExecutor(
        transport=transport,
        timeout_seconds=validated_timeout_seconds,
    )
    sender = BybitPublicGetRequestSender(request_executor=request_executor)
    public_get_api = BybitPublicGetApi(
        sender=sender,
        response_parser=response_parser,
    )
    return create_bybit_demo_instrument_metadata_reader(public_get_api=public_get_api)
