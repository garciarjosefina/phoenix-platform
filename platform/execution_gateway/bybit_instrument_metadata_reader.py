from urllib.parse import quote

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_INSTRUMENTS_INFO_ENDPOINT
from execution_gateway.bybit_instrument_metadata_response_interpreter import (
    BybitInstrumentMetadataResponseInterpreter,
)
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata

_INFRASTRUCTURE_MESSAGE = "Bybit instrument metadata query infrastructure failure"

# Mismo principio que BybitPositionsReader/BybitOpenOrdersReader/
# BybitWalletBalanceReader (ADR-002): ningún tipo Bybit cruza el Port.
# Cualquier ret_code != 0 o fallo de transporte/parseo se traduce, sin
# excepción, a ExecutionInfrastructureError ya existente.
_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitInstrumentMetadataReader:
    def __init__(
        self,
        public_get_api: BybitPublicGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitInstrumentMetadataResponseInterpreter,
    ) -> None:
        if not isinstance(public_get_api, BybitPublicGetApi):
            raise TypeError(
                f"public_get_api must be BybitPublicGetApi, got: {type(public_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitInstrumentMetadataResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitInstrumentMetadataResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._public_get_api = public_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def query_instrument_metadata(self, *, symbol: str) -> ExecutionInstrumentMetadata:
        # Validación local antes de cualquier I/O -- tipo correcto, no vacío.
        # Deliberadamente NO se valida contra una whitelist local de símbolos
        # conocidos (eso es responsabilidad exclusiva de Bybit vía la
        # respuesta real) ni se normaliza el casing en silencio (Bybit
        # documenta símbolos en mayúsculas, pero mutar el input del llamador
        # sin que lo pida sería una mutación silenciosa peligrosa).
        if not isinstance(symbol, str):
            raise TypeError(f"symbol must be str, got: {type(symbol).__name__}")
        if not symbol or symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        url = self._url_builder.build(endpoint=BYBIT_INSTRUMENTS_INFO_ENDPOINT)
        # category=linear fijo: mismo alcance que Positions/Open Orders Read.
        # symbol URL-encoded -- no es una whitelist de negocio, es
        # construcción correcta de la query string ante cualquier carácter
        # que rompería su sintaxis (espacio, '&', '=', etc.) si se
        # interpolara crudo.
        query_string = f"category=linear&symbol={quote(symbol, safe='')}"

        try:
            response = self._public_get_api.request(url=url, query_string=query_string)
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error

        try:
            return self._response_interpreter.interpret(response=response, requested_symbol=symbol)
        except (BybitApiError, BybitResponseProcessingError) as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
