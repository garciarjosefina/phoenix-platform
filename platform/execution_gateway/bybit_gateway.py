import json
import math
from decimal import Decimal

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError

_SIDE_TO_BYBIT = {"buy": "Buy", "sell": "Sell"}
_ORDER_TYPE_TO_BYBIT = {"market": "Market", "limit": "Limit"}
_DEFAULT_TIME_IN_FORCE = "GTC"
_ORDER_ID_MAX_LEN = 36

# Códigos de retorno de Bybit reconocidos como rechazo de la solicitud de
# orden en sí (la orden fue evaluada y rehusada). Cualquier otro ret_code
# -incluidos autenticación, firma, rate limit, timestamp o servidor- se
# clasifica de forma conservadora como fallo de infraestructura: nunca como
# rechazo de negocio.
_ORDER_REJECTION_RET_CODES = frozenset({10001, 110003, 110004, 110007})

# Fallos concretos y conocidos de la cadena de transporte: errores de
# red/socket/HTTP (urllib.error.URLError y HTTPError son subclases de
# OSError, igual que los timeouts de socket) y respuestas cuyo cuerpo no es
# JSON válido (json.JSONDecodeError, subclase concreta de ValueError que
# sólo se produce ante un body ilegible, nunca ante una validación de
# dominio). Cualquier otra excepción -TypeError, ValueError genérico,
# AttributeError, KeyError, AssertionError- no se envuelve: representa un
# defecto de programación o una invariante rota, no una falla operacional.
_TRANSPORT_FAILURES = (OSError, json.JSONDecodeError)

_INFRASTRUCTURE_MESSAGE = "Bybit execution infrastructure failure"
_ADAPTATION_ERROR_MESSAGE = "Execution request cannot be represented by the selected adapter"


class BybitExecutionGateway:
    def __init__(self, client: BybitDemoClient) -> None:
        if not isinstance(client, BybitDemoClient):
            raise TypeError(
                f"client must be compatible with BybitDemoClient, got: {type(client).__name__}"
            )
        self._client = client

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        bybit_request = self._to_bybit_request(request)
        try:
            bybit_result = self._client.place_order(bybit_request)
        except BybitApiError as error:
            if error.ret_code in _ORDER_REJECTION_RET_CODES:
                return self._to_rejected_result(request=request, error=error)
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
        except _TRANSPORT_FAILURES as error:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE) from error
        return self._to_execution_result(request=request, result=bybit_result)

    def _to_bybit_request(self, request: ExecutionRequest) -> BybitCreateOrderRequest:
        if len(request.order_id) > _ORDER_ID_MAX_LEN:
            raise ExecutionRequestNotSupportedError(message=_ADAPTATION_ERROR_MESSAGE)
        return BybitCreateOrderRequest(
            symbol=request.symbol,
            side=_SIDE_TO_BYBIT[request.side],
            order_type=_ORDER_TYPE_TO_BYBIT[request.order_type],
            quantity=_to_plain_decimal(request.quantity),
            price=_to_plain_decimal(request.price) if request.price is not None else None,
            time_in_force=_DEFAULT_TIME_IN_FORCE,
            reduce_only=False,
            order_link_id=request.order_id,
        )

    def _to_execution_result(
        self, *, request: ExecutionRequest, result: BybitCreateOrderResult
    ) -> ExecutionResult:
        if result.order_link_id != request.order_id:
            raise ExecutionInfrastructureError(message=_INFRASTRUCTURE_MESSAGE)
        return ExecutionResult(
            order_id=request.order_id,
            status="accepted",
            exchange_order_id=result.order_id,
        )

    def _to_rejected_result(
        self, *, request: ExecutionRequest, error: BybitApiError
    ) -> ExecutionResult:
        return ExecutionResult(
            order_id=request.order_id,
            status="rejected",
            error_message=error.ret_msg,
        )


def _to_plain_decimal(value: float) -> Decimal:
    if not math.isfinite(value):
        raise ExecutionRequestNotSupportedError(message=_ADAPTATION_ERROR_MESSAGE)
    return Decimal(str(value))
