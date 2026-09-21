from urllib.parse import quote

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT
from execution_gateway.bybit_order_realtime_response_interpreter import (
    BybitOrderRealtimeResponseInterpreter,
)
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderLookupResult

_INFRASTRUCTURE_MESSAGE = "Bybit order realtime lookup infrastructure failure"

_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitOrderRealtimeLookup:
    """Hito 3.88: primitiva read-side aislada, hermana de
    `BybitOrderHistoryLookup` (Hito 3.86).

    Consulta `GET /v5/order/realtime` filtrado por `orderLinkId` para un
    `ExecutionOrderId` propio, y devuelve `BybitRealtimeOrderLookupResult
    | BybitOrderHistoryOrderFound` tipado (nunca `None`).

    Deliberadamente NO envía `openOnly`: la documentación oficial confirma
    que ese parámetro se ignora cuando la consulta filtra por
    `orderId`/`orderLinkId`, así que incluirlo comunicaría una garantía
    inexistente en vez de aportar comportamiento real.

    NO implementa: recovery worker/orchestration, reconocimiento de
    `110072`, `OrderIdentityReportedDuplicateByExchange`, comparador
    económico, append al Ledger, PostgreSQL, `ExecutionLedgerWriter`,
    reintento/reenvío remoto, Projection, Repair. Todo eso queda para
    hitos posteriores (ver ADR-013)."""

    def __init__(
        self,
        private_get_api: BybitPrivateGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitOrderRealtimeResponseInterpreter,
    ) -> None:
        if not isinstance(private_get_api, BybitPrivateGetApi):
            raise TypeError(
                f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitOrderRealtimeResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitOrderRealtimeResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._private_get_api = private_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def lookup_by_execution_order_id(
        self, *, execution_order_id: ExecutionOrderId
    ) -> BybitRealtimeOrderLookupResult | BybitOrderHistoryOrderFound:
        if not isinstance(execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(execution_order_id).__name__}"
            )

        url = self._url_builder.build(endpoint=BYBIT_OPEN_ORDERS_ENDPOINT)
        # category=linear: mismo alcance que el resto del read-side.
        # Sólo orderLinkId como filtro -- nunca symbol/orderId/openOnly.
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
