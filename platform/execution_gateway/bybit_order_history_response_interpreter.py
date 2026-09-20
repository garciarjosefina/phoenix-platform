from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import (
    BybitOrderHistoryLookupResult,
    BybitOrderHistoryOrderFound,
    BybitOrderHistoryOrderNotFound,
)

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

_SIDE_FROM_BYBIT = {"Buy": "buy", "Sell": "sell"}
_ORDER_TYPE_FROM_BYBIT = {"Market": "market", "Limit": "limit"}
# Hito 3.86 / ADR-012 D1-D3: únicamente estos tres estados closed son
# admisibles para una orden Phoenix (ver order_history_lookup_contracts.py).
# Cualquier otro orderStatus -- incluidos los abiertos (New/PartiallyFilled/
# Untriggered/Triggered) y los closed estructuralmente imposibles para este
# scope (Deactivated/PartiallyFilledCanceled) -- falla cerrado: Opción B de
# la decisión registrada en el Hito 3.86 (el interpreter falla cerrado en
# vez de devolver una representación raw sin tipar), exactamente la misma
# arquitectura que ADR-012 D3 ya fijó para el futuro OrderObservedClosed.
_REMOTE_STATUS_FROM_BYBIT = {
    "Filled": "filled",
    "Cancelled": "cancelled",
    "Rejected": "rejected",
}

_REQUIRED_FIELDS = (
    "orderId", "orderLinkId", "symbol", "side", "orderType", "qty", "cumExecQty",
    "cumExecValue", "orderStatus", "reduceOnly", "createdTime", "updatedTime",
)


def _to_finite_decimal(value: object) -> Decimal:
    if not isinstance(value, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    try:
        parsed = Decimal(value)
    except InvalidOperation as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error
    if not parsed.is_finite():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    return parsed


def _to_optional_price_decimal(value: object) -> Decimal | None:
    # Mismo tratamiento que price en Open Orders Read (IMPORTANT-1, auditoría
    # del Hito 3.71): "" o ausente, y también "0" (comparado por valor tras
    # parsear), significan "sin precio preestablecido" -- confirmado como
    # respuesta legítima real de Bybit para market orders en ese mismo campo
    # ("price") del mismo family de endpoints v5/order/*.
    if value is None or value == "":
        return None
    parsed = _to_finite_decimal(value)
    if parsed == 0:
        return None
    return parsed


def _to_optional_avg_price_decimal(value: object) -> Decimal | None:
    # Deliberadamente MÁS CONSERVADOR que _to_optional_price_decimal: la
    # documentación oficial de avgPrice sólo confirma "" como sentinel de
    # ausencia ("returns \"\" for those orders without avg price") -- a
    # diferencia de price, no hay evidencia de que "0" sea también una
    # respuesta legítima para avgPrice. Un avgPrice=="0" con ejecución real
    # (filled_quantity > 0) no se reinterpreta silenciosamente como None:
    # pasa como Decimal("0") y la invariante average_price > 0 del contrato
    # lo rechaza -- fail-closed ante un dato inconsistente en vez de
    # inventar un segundo sentinel sin evidencia (MENOR pendiente de
    # confirmación empírica en Bybit Demo).
    if value is None or value == "":
        return None
    return _to_finite_decimal(value)


def _to_optional_non_empty_str(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    return value


def _to_optional_reject_reason(value: object) -> str | None:
    # ADR-012 D8: verbatim; None cuando ausente o exactamente "EC_NoError"
    # (el propio sentinel de "sin motivo de rechazo" de la taxonomía oficial
    # de Bybit, distinto de una cadena vacía).
    text = _to_optional_non_empty_str(value)
    if text == "EC_NoError":
        return None
    return text


def _to_timestamp_ms(value: object, *, field: str) -> int:
    if not isinstance(value, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    try:
        parsed = int(value)
    except ValueError as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error
    if parsed < 0:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    return parsed


def _interpret_history_item(
    item: object, *, execution_order_id: ExecutionOrderId, server_time_ms: int
) -> BybitOrderHistoryOrderFound:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    exchange_order_id = item["orderId"]
    if not isinstance(exchange_order_id, str) or not exchange_order_id or exchange_order_id.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    # Correlación: aunque la query ya filtró por orderLinkId, la respuesta
    # remota nunca se confía sin verificar (mismo principio que la
    # verificación de symbol en Instrument Metadata Read, Hito 3.73, y que
    # la verificación de orderLinkId post-ACK en bybit_gateway.py). Un
    # mismatch, un orderLinkId ausente/vacío, o el uso de exchange_order_id
    # como sustituto NUNCA se toleran -- fail-closed incondicional.
    order_link_id = item["orderLinkId"]
    if not isinstance(order_link_id, str) or not order_link_id or order_link_id.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    if order_link_id != execution_order_id.value:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    symbol = item["symbol"]
    if not isinstance(symbol, str) or not symbol or symbol.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    side_raw = item["side"]
    if side_raw not in _SIDE_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    side = _SIDE_FROM_BYBIT[side_raw]

    order_type_raw = item["orderType"]
    if order_type_raw not in _ORDER_TYPE_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    order_type = _ORDER_TYPE_FROM_BYBIT[order_type_raw]

    status_raw = item["orderStatus"]
    if status_raw not in _REMOTE_STATUS_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    remote_status = _REMOTE_STATUS_FROM_BYBIT[status_raw]

    reduce_only = item["reduceOnly"]
    if not isinstance(reduce_only, bool):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    quantity = _to_finite_decimal(item["qty"])
    filled_quantity = _to_finite_decimal(item["cumExecQty"])
    filled_value = _to_finite_decimal(item["cumExecValue"])
    price = _to_optional_price_decimal(item.get("price"))
    average_price = _to_optional_avg_price_decimal(item.get("avgPrice"))
    # cancelType: sin sentinel documentado para órdenes no canceladas
    # (MENOR-1, ADR-012) -- "" o ausente se tratan como None, igual que el
    # resto de campos opcionales de string de este bounded context; CUALQUIER
    # otro valor se preserva verbatim y queda sujeto a la invariante del
    # contrato (cancel_type debe ser None si remote_status != "cancelled"),
    # que falla cerrado ante un valor inesperado en vez de descartarlo en
    # silencio. Requiere validación empírica contra Bybit Demo.
    cancel_type = _to_optional_non_empty_str(item.get("cancelType"))
    reject_reason = _to_optional_reject_reason(item.get("rejectReason"))

    remote_created_time_ms = _to_timestamp_ms(item["createdTime"], field="createdTime")
    remote_updated_time_ms = _to_timestamp_ms(item["updatedTime"], field="updatedTime")

    try:
        return BybitOrderHistoryOrderFound(
            execution_order_id=execution_order_id,
            exchange_order_id=exchange_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            filled_quantity=filled_quantity,
            filled_value=filled_value,
            remote_status=remote_status,
            reduce_only=reduce_only,
            server_time_ms=server_time_ms,
            remote_created_time_ms=remote_created_time_ms,
            remote_updated_time_ms=remote_updated_time_ms,
            price=price,
            average_price=average_price,
            cancel_type=cancel_type,
            reject_reason=reject_reason,
        )
    except (TypeError, ValueError) as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


class BybitOrderHistoryResponseInterpreter:
    def interpret(
        self, *, response: BybitResponse, execution_order_id: ExecutionOrderId
    ) -> BybitOrderHistoryLookupResult:
        if not isinstance(response, BybitResponse):
            raise TypeError(f"response must be BybitResponse, got: {type(response).__name__}")
        if not isinstance(execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(execution_order_id).__name__}"
            )

        if response.ret_code != 0:
            raise BybitApiError(ret_code=response.ret_code, ret_msg=response.ret_msg)

        result = response.result
        if not isinstance(result, Mapping):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        if "list" not in result:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
        raw_list = result["list"]
        if not isinstance(raw_list, tuple):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # Fail-closed ante paginación -- mismo principio que Open Orders/
        # Instrument Metadata Read. La documentación oficial de
        # /v5/order/history no garantiza que nextPageCursor permanezca vacío
        # para una consulta filtrada por un orderLinkId exacto; se trata
        # cualquier valor truthy como señal de una respuesta potencialmente
        # incompleta, nunca se sirve un resultado parcial ni se sigue el
        # cursor en un loop (Hito 3.86, §17).
        if result.get("nextPageCursor"):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # Cardinalidad (Hito 3.86, §7): 0 -> NOT_FOUND (resultado legítimo,
        # nunca un error); >1 -> fail-closed (respuesta ambigua/corrupta,
        # nunca se elige arbitrariamente el primero); exactamente 1 ->
        # interpretar, con verificación de correlación incondicional dentro
        # de _interpret_history_item.
        if len(raw_list) == 0:
            return BybitOrderHistoryOrderNotFound()
        if len(raw_list) > 1:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        return _interpret_history_item(
            raw_list[0], execution_order_id=execution_order_id, server_time_ms=response.time_ms
        )
