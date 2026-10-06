from collections.abc import Mapping

from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionAccepted,
    SubmissionIdentityDuplicate,
    SubmissionOutcomeUnknown,
    SubmissionRejected,
)

# Hito 3.96 / ADR-015 D8: único conjunto de `ret_code` clasificado como rechazo
# de negocio de la orden (la orden fue evaluada y rehusada). Mismo conjunto que
# usa `BybitExecutionGateway` (que permanece byte-idéntico); se declara aquí
# otra vez, a propósito, para no importar un nombre privado de un componente
# aceptado -- la igualdad entre ambos se fija desde los tests.
_ORDER_REJECTION_RET_CODES = frozenset({10001, 110003, 110004, 110007})

# ADR-013 D3: "identidad duplicada" -- evidencia de existencia de la
# identidad, nunca un rechazo ni una aceptación de la orden.
_DUPLICATE_IDENTITY_RET_CODE = 110072

_SUCCESS_RET_CODE = 0


class BybitOrderSubmissionResponseInterpreter:
    """Traduce el `BybitResponse` COMPLETO de create-order (ya parseado por el
    parser aceptado, con `ret_code`/`ret_msg`/`time` intactos) a un
    `OrderSubmissionOutcome`. Reemplaza, para este camino, a
    `BybitCreateOrderResponseInterpreter`, que descarta `time_ms` y convierte
    todo `ret_code != 0` en una excepción.

    Pura y determinista: sin red, sin reloj, sin estado. Los datos remotos se
    preservan literalmente (`ret_msg`, `orderId`, `time_ms` del response);
    nunca se inventa, normaliza ni reconstruye ninguno. Todo `ret_code` fuera
    de éxito / `110072` / conjunto de rechazo es ambiguo
    (`ambiguous_business_response`), nunca un rechazo (ADR-015 D8).

    No lanza por una respuesta remota, conocida o ambigua: la DEVUELVE como
    outcome. Los errores de programación (`TypeError` por argumentos de tipo
    incorrecto) se propagan.
    """

    def interpret(
        self,
        *,
        response: BybitResponse,
        expected_order_link_id: str,
    ) -> OrderSubmissionOutcome:
        if not isinstance(response, BybitResponse):
            raise TypeError(
                f"response must be BybitResponse, got: {type(response).__name__}"
            )
        if not isinstance(expected_order_link_id, str):
            raise TypeError(
                f"expected_order_link_id must be str, got: {type(expected_order_link_id).__name__}"
            )
        if not expected_order_link_id or expected_order_link_id.isspace():
            raise ValueError("expected_order_link_id must not be empty or whitespace-only")

        ret_code = response.ret_code
        if ret_code == _SUCCESS_RET_CODE:
            return self._interpret_success(
                response=response, expected_order_link_id=expected_order_link_id
            )
        if ret_code == _DUPLICATE_IDENTITY_RET_CODE:
            if _is_blank(response.ret_msg):
                return SubmissionOutcomeUnknown(reason="malformed_response")
            return SubmissionIdentityDuplicate(
                ret_code=ret_code,
                ret_msg=response.ret_msg,
                server_time_ms=response.time_ms,
            )
        if ret_code in _ORDER_REJECTION_RET_CODES:
            if _is_blank(response.ret_msg):
                return SubmissionOutcomeUnknown(reason="malformed_response")
            return SubmissionRejected(
                ret_code=ret_code,
                ret_msg=response.ret_msg,
                server_time_ms=response.time_ms,
            )
        return SubmissionOutcomeUnknown(reason="ambiguous_business_response")

    def _interpret_success(
        self,
        *,
        response: BybitResponse,
        expected_order_link_id: str,
    ) -> OrderSubmissionOutcome:
        result = response.result
        if not isinstance(result, Mapping):
            return SubmissionOutcomeUnknown(reason="malformed_response")
        if "orderId" not in result or "orderLinkId" not in result:
            return SubmissionOutcomeUnknown(reason="malformed_response")

        # Mismo contrato aceptado que usa el camino legacy para validar la
        # forma de `result`; sólo se envuelven los errores de VALIDACIÓN DE
        # DATOS REMOTOS de este único constructor.
        try:
            confirmed = BybitCreateOrderResult(
                order_id=result["orderId"],
                order_link_id=result["orderLinkId"],
            )
        except (TypeError, ValueError):
            return SubmissionOutcomeUnknown(reason="malformed_response")

        if confirmed.order_link_id != expected_order_link_id:
            return SubmissionOutcomeUnknown(reason="identity_mismatch")

        return SubmissionAccepted(
            exchange_order_id=confirmed.order_id,
            server_time_ms=response.time_ms,
        )


def _is_blank(value: str) -> bool:
    return not value or value.isspace()


__all__ = ["BybitOrderSubmissionResponseInterpreter"]
