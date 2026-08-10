from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_POSITIONS_ENDPOINT
from execution_gateway.bybit_positions_response_interpreter import BybitPositionsResponseInterpreter
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.positions_contracts import PositionsSnapshot

# Alcance inicial fijado deliberadamente a linear/USDT (Hito 3.70): Phoenix
# opera únicamente derivados lineares de Bybit. `settleCoin` es obligatorio
# en la API V5 cuando no se filtra por `symbol` (documentado oficialmente por
# Bybit). `limit=200` es el máximo de página soportado por Bybit -- no se
# implementa paginación en este hito (deuda documentada, no bloqueante);
# con el máximo de página ya solicitado, una segunda página sólo sería
# necesaria con más de 200 posiciones simultáneas en una única cuenta Demo,
# escenario fuera de alcance para este hito.
_QUERY_STRING = "category=linear&settleCoin=USDT&limit=200"

_INFRASTRUCTURE_MESSAGE = "Bybit position query infrastructure failure"

# Mismo principio que bybit_gateway.py (ADR-001A / Core Hardening Pack A):
# ningún tipo Bybit cruza el Port. A diferencia de la escritura, una lectura
# no tiene noción de "rechazo de negocio" -- cualquier ret_code != 0 o fallo
# de transporte/parseo se traduce, sin excepción, a la misma
# ExecutionInfrastructureError ya usada por el Port de ejecución (sin
# inventar una jerarquía nueva).
_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitPositionsReader:
    def __init__(
        self,
        private_get_api: BybitPrivateGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitPositionsResponseInterpreter,
    ) -> None:
        if not isinstance(private_get_api, BybitPrivateGetApi):
            raise TypeError(
                f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitPositionsResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitPositionsResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._private_get_api = private_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def query_positions(self) -> PositionsSnapshot:
        url = self._url_builder.build(endpoint=BYBIT_POSITIONS_ENDPOINT)

        try:
            response = self._private_get_api.request(url=url, query_string=_QUERY_STRING)
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error

        try:
            return self._response_interpreter.interpret(response=response)
        except (BybitApiError, BybitResponseProcessingError) as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
