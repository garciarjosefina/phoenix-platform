from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT
from execution_gateway.bybit_open_orders_response_interpreter import BybitOpenOrdersResponseInterpreter
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot

# category=linear/settleCoin=USDT: mismo alcance que Positions Read (Hito
# 3.70) -- Phoenix opera únicamente derivados lineares USDT. limit=50 es el
# máximo de página documentado por Bybit V5 para /v5/order/realtime (a
# diferencia de /v5/position/list, cuyo máximo es 200) -- basado en la
# especificación oficial publicada, no confirmado contra una respuesta real
# en este hito. Sin paginación (deuda documentada, ver ADR-002): el
# interpreter falla cerrado ante cualquier nextPageCursor no vacío en vez
# de servir un snapshot truncado.
_QUERY_STRING = "category=linear&settleCoin=USDT&limit=50"

_INFRASTRUCTURE_MESSAGE = "Bybit open orders query infrastructure failure"

# Mismo principio que BybitPositionsReader/bybit_gateway.py (ADR-001A /
# ADR-002): ningún tipo Bybit cruza el Port. Una lectura no tiene noción de
# "rechazo de negocio" -- cualquier ret_code != 0 o fallo de
# transporte/parseo se traduce, sin excepción, a ExecutionInfrastructureError
# ya existente.
_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitOpenOrdersReader:
    def __init__(
        self,
        private_get_api: BybitPrivateGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitOpenOrdersResponseInterpreter,
    ) -> None:
        if not isinstance(private_get_api, BybitPrivateGetApi):
            raise TypeError(
                f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitOpenOrdersResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitOpenOrdersResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._private_get_api = private_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def query_open_orders(self) -> OpenOrdersSnapshot:
        url = self._url_builder.build(endpoint=BYBIT_OPEN_ORDERS_ENDPOINT)

        try:
            response = self._private_get_api.request(url=url, query_string=_QUERY_STRING)
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error

        try:
            return self._response_interpreter.interpret(response=response)
        except (BybitApiError, BybitResponseProcessingError) as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
