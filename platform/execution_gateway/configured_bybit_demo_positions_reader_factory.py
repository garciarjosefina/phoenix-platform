from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.bybit_demo_positions_reader_factory import create_bybit_demo_positions_reader
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_positions_reader import BybitPositionsReader
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_private_get_request_sender import BybitPrivateGetRequestSender
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_get_request_executor import HttpGetRequestExecutor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.millisecond_clock_factory import create_millisecond_clock
from execution_gateway.urllib_get_http_transport import UrllibGetHttpTransport


def create_configured_bybit_demo_positions_reader(
    *,
    config: BybitDemoExecutionConfig,
) -> BybitPositionsReader:
    if not isinstance(config, BybitDemoExecutionConfig):
        raise TypeError(
            f"config must be BybitDemoExecutionConfig, got: {type(config).__name__}"
        )
    # Mismas credenciales/reloj/firma/recv_window que el Port de ejecución
    # (Hito 3.62) -- Bybit Demo usa una única API key para lectura y
    # escritura, y el esquema de firma HMAC es idéntico en ambos caminos.
    credentials = create_bybit_demo_credentials(
        api_key=config.api_key,
        api_secret=config.api_secret,
    )
    signer = create_message_signer()
    clock = create_millisecond_clock()
    validated_recv_window_ms = create_bybit_recv_window_ms(recv_window_ms=config.recv_window_ms)
    authenticator = create_bybit_authenticator(
        credentials=credentials,
        clock=clock,
        signer=signer,
        recv_window_ms=validated_recv_window_ms,
    )
    serializer = create_json_serializer()
    header_builder = create_bybit_header_builder()
    response_parser = create_bybit_response_parser(serializer=serializer)

    transport = UrllibGetHttpTransport()
    validated_timeout_seconds = create_http_timeout_seconds(timeout_seconds=config.timeout_seconds)
    request_executor = HttpGetRequestExecutor(
        transport=transport,
        timeout_seconds=validated_timeout_seconds,
    )
    sender = BybitPrivateGetRequestSender(
        authenticator=authenticator,
        header_builder=header_builder,
        request_executor=request_executor,
    )
    private_get_api = BybitPrivateGetApi(
        sender=sender,
        response_parser=response_parser,
    )
    return create_bybit_demo_positions_reader(private_get_api=private_get_api)
