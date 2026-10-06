from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT
from execution_gateway.bybit_order_submission_response_interpreter import (
    BybitOrderSubmissionResponseInterpreter,
)
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.canonical_execution_decimal import canonical_execution_decimal
from execution_gateway.contracts import ExecutionRequest
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionOutcomeUnknown,
)

_SIDE_TO_BYBIT = {"buy": "Buy", "sell": "Sell"}
_ORDER_TYPE_TO_BYBIT = {"market": "Market", "limit": "Limit"}
_DEFAULT_TIME_IN_FORCE = "GTC"
_ORDER_ID_MAX_LEN = 36

_ADAPTATION_ERROR_MESSAGE = "Execution request cannot be represented by the selected adapter"


class BybitOrderSubmissionAdapter:
    """Adapter Bybit de `OrderSubmissionPort` (Hito 3.96, nodo [f] de
    ADR-015/ADR-016). Hermano de `BybitExecutionGateway`, que permanece
    byte-idéntico: compone el payload builder y el endpoint executor ya
    aceptados con un interpreter propio que preserva el `BybitResponse`
    completo (`ret_code`, `ret_msg`, `time_ms`).

    UNA sola llamada remota por `submit`, siempre: ningún reintento, ningún
    segundo request, ninguna identidad nueva (ADR-015 D2/D9). La identidad
    Phoenix de la orden ya viaja en `request.order_id` (ADR-015 D7 paso 3: el
    coordinador la valida como `ExecutionOrderId`) y se usa tal cual como
    `orderLinkId`; este adapter no genera, deriva ni sustituye ninguna
    identidad, y no conoce cuenta, Ledger ni `ExecutionOrderId`.

    Contrato de excepciones (el que fija el Protocol):
    - un request no representable, detectado ANTES de cualquier red, levanta
      `ExecutionRequestNotSupportedError` (cero llamadas al transporte);
    - todo resultado remoto -- conocido o ambiguo -- se DEVUELVE como outcome;
    - fallos de red (`OSError`, que incluye timeouts, DNS, reset y
      `urllib.error.HTTPError`/`URLError`) ⇒ `Unknown(transport_failure)`,
      sin discriminar known-not-sent (ADR-011 D7);
    - respuesta recibida pero no procesable (`BybitResponseProcessingError`)
      ⇒ `Unknown(malformed_response)`;
    - cualquier otra excepción (defecto de programación o invariante rota)
      se propaga sin envolver (ADR-001A / ADR-015 D9).
    """

    def __init__(
        self,
        payload_builder: BybitCreateOrderPayloadBuilder,
        endpoint_executor: BybitEndpointExecutor,
        response_interpreter: BybitOrderSubmissionResponseInterpreter,
    ) -> None:
        if not isinstance(payload_builder, BybitCreateOrderPayloadBuilder):
            raise TypeError(
                f"payload_builder must be BybitCreateOrderPayloadBuilder, got: {type(payload_builder).__name__}"
            )
        if not isinstance(endpoint_executor, BybitEndpointExecutor):
            raise TypeError(
                f"endpoint_executor must be BybitEndpointExecutor, got: {type(endpoint_executor).__name__}"
            )
        if not isinstance(response_interpreter, BybitOrderSubmissionResponseInterpreter):
            raise TypeError(
                "response_interpreter must be BybitOrderSubmissionResponseInterpreter, "
                f"got: {type(response_interpreter).__name__}"
            )
        self._payload_builder = payload_builder
        self._endpoint_executor = endpoint_executor
        self._response_interpreter = response_interpreter

    def submit(self, request: ExecutionRequest) -> OrderSubmissionOutcome:
        if not isinstance(request, ExecutionRequest):
            raise TypeError(
                f"request must be ExecutionRequest, got: {type(request).__name__}"
            )

        # Todo lo que puede ser rechazado localmente ocurre ANTES de la red.
        bybit_request = self._to_bybit_request(request)
        payload = self._payload_builder.build(request=bybit_request)

        # Única llamada remota. Sólo se capturan fallos concretos y conocidos
        # de transporte/respuesta -- nunca `Exception`.
        try:
            response = self._endpoint_executor.execute(
                endpoint=BYBIT_CREATE_ORDER_ENDPOINT,
                payload=payload,
            )
        except OSError:
            return SubmissionOutcomeUnknown(reason="transport_failure")
        except BybitResponseProcessingError:
            return SubmissionOutcomeUnknown(reason="malformed_response")

        return self._response_interpreter.interpret(
            response=response,
            expected_order_link_id=request.order_id,
        )

    def _to_bybit_request(self, request: ExecutionRequest) -> BybitCreateOrderRequest:
        # Misma economía y mismo mapping que `BybitExecutionGateway`
        # (paridad de payload fijada desde los tests); la conversión
        # float -> Decimal es SIEMPRE la autoridad canónica de 3.92.
        if len(request.order_id) > _ORDER_ID_MAX_LEN:
            raise ExecutionRequestNotSupportedError(message=_ADAPTATION_ERROR_MESSAGE)
        return BybitCreateOrderRequest(
            symbol=request.symbol,
            side=_SIDE_TO_BYBIT[request.side],
            order_type=_ORDER_TYPE_TO_BYBIT[request.order_type],
            quantity=canonical_execution_decimal(request.quantity),
            price=canonical_execution_decimal(request.price) if request.price is not None else None,
            time_in_force=_DEFAULT_TIME_IN_FORCE,
            reduce_only=False,
            order_link_id=request.order_id,
        )


__all__ = ["BybitOrderSubmissionAdapter"]
