from execution_gateway.bybit_authenticator_factory import create_bybit_authenticator
from execution_gateway.bybit_demo_credentials_factory import create_bybit_demo_credentials
from execution_gateway.bybit_demo_execution_gateway_factory import create_bybit_demo_execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_header_builder_factory import create_bybit_header_builder
from execution_gateway.bybit_private_api_factory import create_bybit_private_api
from execution_gateway.bybit_private_request_sender_factory import create_bybit_private_request_sender
from execution_gateway.bybit_recv_window_factory import create_bybit_recv_window_ms
from execution_gateway.bybit_request_builder_factory import create_bybit_request_builder
from execution_gateway.bybit_response_parser_factory import create_bybit_response_parser
from execution_gateway.http_request_executor_factory import create_http_request_executor
from execution_gateway.http_timeout_factory import create_http_timeout_seconds
from execution_gateway.http_transport_factory import create_http_transport
from execution_gateway.json_serializer_factory import create_json_serializer
from execution_gateway.message_signer_factory import create_message_signer
from execution_gateway.millisecond_clock_factory import create_millisecond_clock


def create_configured_bybit_demo_execution_gateway(
    *,
    api_key: str,
    api_secret: str,
    recv_window_ms: int,
    timeout_seconds: int | float,
) -> BybitExecutionGateway:
    credentials = create_bybit_demo_credentials(
        api_key=api_key,
        api_secret=api_secret,
    )
    signer = create_message_signer()
    clock = create_millisecond_clock()
    validated_recv_window_ms = create_bybit_recv_window_ms(recv_window_ms=recv_window_ms)
    authenticator = create_bybit_authenticator(
        credentials=credentials,
        clock=clock,
        signer=signer,
        recv_window_ms=validated_recv_window_ms,
    )
    serializer = create_json_serializer()
    header_builder = create_bybit_header_builder()
    request_builder = create_bybit_request_builder(
        serializer=serializer,
        authenticator=authenticator,
        header_builder=header_builder,
    )
    response_parser = create_bybit_response_parser(serializer=serializer)
    transport = create_http_transport()
    validated_timeout_seconds = create_http_timeout_seconds(timeout_seconds=timeout_seconds)
    request_executor = create_http_request_executor(
        transport=transport,
        timeout_seconds=validated_timeout_seconds,
    )
    sender = create_bybit_private_request_sender(
        request_builder=request_builder,
        request_executor=request_executor,
    )
    private_api = create_bybit_private_api(
        sender=sender,
        response_parser=response_parser,
    )
    return create_bybit_demo_execution_gateway(private_api=private_api)
