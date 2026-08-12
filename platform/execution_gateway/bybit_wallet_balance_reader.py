from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoints import BYBIT_WALLET_BALANCE_ENDPOINT
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.bybit_wallet_balance_response_interpreter import (
    BybitWalletBalanceResponseInterpreter,
)
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot

# accountType=UNIFIED es el único valor documentado por Bybit V5 para
# /v5/account/wallet-balance compatible con una cuenta que opera derivados
# lineares USDT (confirmado contra la documentación oficial: el enum
# accountType de este endpoint sólo admite UNIFIED o FUND -- FUND es la
# billetera de depósito/retiro, fuera de alcance). No se pasa `coin`: se
# omite deliberadamente para que Bybit devuelva todas las monedas con saldo
# no-cero de la cuenta (comportamiento documentado por defecto) -- fijar
# `coin=USDT` ocultaría en silencio cualquier otra moneda presente,
# exactamente lo que la Decisión de "no descartar monedas desconocidas" de
# este hito prohíbe.
_QUERY_STRING = "accountType=UNIFIED"

_INFRASTRUCTURE_MESSAGE = "Bybit wallet balance query infrastructure failure"

# Mismo principio que BybitPositionsReader/BybitOpenOrdersReader (ADR-002):
# ningún tipo Bybit cruza el Port. Una lectura no tiene noción de "rechazo de
# negocio" -- cualquier ret_code != 0 o fallo de transporte/parseo se
# traduce, sin excepción, a ExecutionInfrastructureError ya existente.
_TRANSPORT_FAILURES = (OSError, BybitResponseProcessingError)


class BybitWalletBalanceReader:
    def __init__(
        self,
        private_get_api: BybitPrivateGetApi,
        url_builder: BybitUrlBuilder,
        response_interpreter: BybitWalletBalanceResponseInterpreter,
    ) -> None:
        if not isinstance(private_get_api, BybitPrivateGetApi):
            raise TypeError(
                f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
            )
        if not isinstance(url_builder, BybitUrlBuilder):
            raise TypeError(
                f"url_builder must be BybitUrlBuilder, got: {type(url_builder).__name__}"
            )
        if not isinstance(response_interpreter, BybitWalletBalanceResponseInterpreter):
            raise TypeError(
                f"response_interpreter must be BybitWalletBalanceResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._private_get_api = private_get_api
        self._url_builder = url_builder
        self._response_interpreter = response_interpreter

    def query_wallet_balance(self) -> WalletBalanceSnapshot:
        url = self._url_builder.build(endpoint=BYBIT_WALLET_BALANCE_ENDPOINT)

        try:
            response = self._private_get_api.request(url=url, query_string=_QUERY_STRING)
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error

        try:
            return self._response_interpreter.interpret(response=response)
        except (BybitApiError, BybitResponseProcessingError) as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
