import urllib.request
from collections.abc import Mapping

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_demo_execution_gateway_env_bootstrap import (
    bootstrap_bybit_demo_execution_gateway_from_env,
)
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.smoke_test_result import SmokeTestResult

_ENVIRONMENT = "demo"
_EMPTY_BODY = ""
_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

# GET /v5/user/query-api ("Query API Key Information"): endpoint de
# diagnóstico oficial de Bybit V5, sin parámetros. Verifica en una sola
# llamada exactamente lo que este smoke test necesita -- credenciales
# válidas, firma HMAC aceptada, timestamp y recv_window dentro de ventana, y
# permisos de la API key -- sin leer ni modificar órdenes, posiciones,
# balances ni configuración. Es de sólo lectura por diseño: introspecciona
# la propia API key que firma la solicitud, no ningún recurso de la cuenta.
_SMOKE_TEST_ENDPOINT = BybitEndpoint(method="GET", path="/v5/user/query-api")


def _extract_authenticated_pipeline(gateway: BybitExecutionGateway) -> dict[str, object]:
    # El gateway no expone estos componentes como API pública. Se reutilizan
    # los objetos que el bootstrap (Hito 3.66) ya construyó y validó --
    # credenciales, signer, reloj, authenticator y parser -- sin volver a
    # construir el grafo.
    sender = gateway._client._create_order_operation._endpoint_executor._private_api._sender
    return dict(
        base_url=gateway._client._create_order_operation._endpoint_executor._url_builder._base_url,
        authenticator=sender._request_builder._authenticator,
        header_builder=sender._request_builder._header_builder,
        response_parser=gateway._client._create_order_operation._endpoint_executor._private_api._response_parser,
        timeout_seconds=sender._request_executor._timeout_seconds,
    )


def _get(*, url: str, headers: Mapping[str, str], timeout_seconds: float) -> str:
    request = urllib.request.Request(url=url, headers=headers, method=_SMOKE_TEST_ENDPOINT.method)
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        response_body = response.read()
    try:
        return response_body.decode("utf-8")
    except UnicodeDecodeError as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


def smoke_test_bybit_demo_connection(
    *,
    environ: Mapping[str, str] | None = None,
) -> SmokeTestResult:
    gateway = bootstrap_bybit_demo_execution_gateway_from_env(environ=environ)
    pipeline = _extract_authenticated_pipeline(gateway)

    authentication = pipeline["authenticator"].authenticate(body=_EMPTY_BODY)
    headers = pipeline["header_builder"].build(authentication=authentication)
    url = pipeline["base_url"] + _SMOKE_TEST_ENDPOINT.path

    response_text = _get(url=url, headers=headers, timeout_seconds=pipeline["timeout_seconds"])
    response = pipeline["response_parser"].parse(response_text=response_text)

    if response.ret_code != 0:
        raise BybitApiError(ret_code=response.ret_code, ret_msg=response.ret_msg)

    return SmokeTestResult(
        success=True,
        endpoint=_SMOKE_TEST_ENDPOINT.path,
        environment=_ENVIRONMENT,
        server_time=response.time_ms,
    )
