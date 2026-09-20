from urllib.parse import quote

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_ORDER_HISTORY_ENDPOINT
from execution_gateway.bybit_order_history_response_interpreter import BybitOrderHistoryResponseInterpreter
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryLookupResult

_INFRASTRUCTURE_MESSAGE = "Bybit order history lookup infrastructure failure"

# Mismo principio que el resto del read-side (ADR-001A/ADR-002): ningún tipo
# Bybit cruza el Port. Cualquier ret_code != 0 (salvo el caso NOT_FOUND, que
# no es un error sino result.list vacío con ret_code == 0) o fallo de
# transporte/parseo se traduce a ExecutionInfrastructureError ya existente.
_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitOrderHistoryLookup:
    """Hito 3.86: primitiva read-side aislada de recovery.

    Consulta `GET /v5/order/history` filtrado por `orderLinkId` para un
    `ExecutionOrderId` propio, y devuelve un `BybitOrderHistoryLookupResult`
    tipado (FOUND/NOT_FOUND explícitos -- nunca `None`).

    NO implementa: recovery worker/orchestration, `OrderObservedClosed`,
    append al Ledger, PostgreSQL, `ExecutionLedgerWriter`, reconocimiento de
    `110072`, reintento/reenvío remoto, fast-path por `/v5/order/realtime`,
    fallback `realtime`->`history`, Projection, Repair, fills ledger,
    cancel/amend, HALT de cuenta. Todo eso queda para hitos posteriores (ver
    ADR-012, Resolución del STOP)."""

    def __init__(
        self,
        private_get_api: BybitPrivateGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitOrderHistoryResponseInterpreter,
    ) -> None:
        if not isinstance(private_get_api, BybitPrivateGetApi):
            raise TypeError(
                f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitOrderHistoryResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitOrderHistoryResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._private_get_api = private_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def lookup_by_execution_order_id(
        self, *, execution_order_id: ExecutionOrderId
    ) -> BybitOrderHistoryLookupResult:
        # Nunca acepta una búsqueda sin identidad Phoenix: sólo ExecutionOrderId,
        # nunca un str crudo ni exchange_order_id como sustituto -- la firma
        # del método hace estructuralmente imposible el fallback prohibido.
        if not isinstance(execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(execution_order_id).__name__}"
            )

        url = self._url_builder.build(endpoint=BYBIT_ORDER_HISTORY_ENDPOINT)
        # category=linear: mismo alcance que el resto del read-side (ADR-002).
        # Sólo orderLinkId como filtro -- nunca symbol/orderId/exchange
        # order id como sustituto de identidad (Hito 3.86, §3/§4). quote()
        # por defensa en profundidad: el charset de ExecutionOrderId
        # ([a-z0-9_] tras "ord_") ya es URL-safe, pero no se asume eso sin
        # encodear, mismo patrón que Instrument Metadata Read (Hito 3.73).
        query_string = f"category=linear&orderLinkId={quote(execution_order_id.value, safe='')}"

        try:
            response = self._private_get_api.request(url=url, query_string=query_string)
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error

        try:
            return self._response_interpreter.interpret(
                response=response, execution_order_id=execution_order_id
            )
        except (BybitApiError, BybitResponseProcessingError) as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
