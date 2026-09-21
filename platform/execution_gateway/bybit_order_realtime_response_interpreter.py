from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import (
    BybitRealtimeOrderFoundOpen,
    BybitRealtimeOrderLookupResult,
    BybitRealtimeOrderNotFound,
)

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

_SIDE_FROM_BYBIT = {"Buy": "buy", "Sell": "sell"}
_ORDER_TYPE_FROM_BYBIT = {"Market": "market", "Limit": "limit"}
# Hito 3.88 / ADR-012 D1-D3 + Hito 3.86 (post-corrección): documentación
# oficial confirma que `openOnly` se IGNORA al filtrar por orderLinkId --
# una consulta por identidad puede devolver legítimamente CUALQUIERA de
# los seis estados que /v5/order/realtime conoce, abiertos o cerrados.
# Se despacha por rama según el estado remoto:
_OPEN_STATUS_FROM_BYBIT = {
    "New": "new",
    "PartiallyFilled": "partially_filled",
}
# Idéntico a _REMOTE_STATUS_FROM_BYBIT de bybit_order_history_response_
# interpreter.py (Hito 3.86) -- una fila cerrada observada vía realtime es
# el MISMO hecho remoto que una observada vía history, y se representa con
# el mismo contrato aceptado (BybitOrderHistoryOrderFound), nunca con un
# tipo paralelo.
_CLOSED_STATUS_FROM_BYBIT = {
    "Filled": "filled",
    "Cancelled": "cancelled",
    "Rejected": "rejected",
}
# Untriggered/Triggered (condicionales -- Phoenix nunca las crea, ver
# order_realtime_lookup_contracts.py) y Deactivated/PartiallyFilledCanceled
# (imposibles para este scope, ADR-012 F2) fallan cerrado sin mapeo.

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
    # Mismo tratamiento que price en Open Orders Read (IMPORTANT-1, Hito
    # 3.71) y en Order History Lookup (Hito 3.86): "" o ausente, y también
    # "0" (comparado por valor), significan "sin precio preestablecido".
    if value is None or value == "":
        return None
    parsed = _to_finite_decimal(value)
    if parsed == 0:
        return None
    return parsed


def _to_optional_avg_price_decimal(value: object) -> Decimal | None:
    # Mismo tratamiento que avgPrice en Order History Lookup tras su
    # corrección post-auditoría (Hito 3.86): "" y "0" son ambos sentinels
    # documentados de ausencia -- confirmado además aquí por el propio
    # ejemplo oficial de /v5/order/realtime (orden New: "avgPrice": "0").
    if value is None or value == "":
        return None
    parsed = _to_finite_decimal(value)
    if parsed == 0:
        return None
    return parsed


def _to_optional_non_empty_str(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    return value


def _to_optional_cancel_type(value: object) -> str | None:
    # Mismo tratamiento que cancelType en Order History Lookup (Hito 3.86,
    # post-corrección): "UNKNOWN" es el sentinel genérico de "sin
    # clasificación aplicable" -- confirmado exactamente por el ejemplo
    # oficial de /v5/order/realtime (orden New: "cancelType": "UNKNOWN").
    text = _to_optional_non_empty_str(value)
    if text == "UNKNOWN":
        return None
    return text


def _to_optional_reject_reason(value: object) -> str | None:
    # ADR-012 D8: verbatim; None cuando ausente o exactamente "EC_NoError"
    # -- confirmado por el mismo ejemplo oficial ("rejectReason":
    # "EC_NoError" en una orden New, nunca rechazada).
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


def _common_fields(item: Mapping, *, execution_order_id: ExecutionOrderId) -> dict:
    """Campos y validaciones idénticos entre la rama abierta y la rama
    cerrada -- identidad, correlación, clasificación de side/order_type,
    reduceOnly, magnitudes económicas y timestamps. La única diferencia
    entre ramas es el mapeo de `orderStatus` y el contrato de destino."""
    for field in _REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    exchange_order_id = item["orderId"]
    if not isinstance(exchange_order_id, str) or not exchange_order_id or exchange_order_id.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    # Correlación incondicional -- mismo principio que Order History Lookup
    # (Hito 3.86): aunque la query ya filtró por orderLinkId, la respuesta
    # remota nunca se confía sin verificar. Nunca exchange_order_id como
    # sustituto.
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

    order_type_raw = item["orderType"]
    if order_type_raw not in _ORDER_TYPE_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    reduce_only = item["reduceOnly"]
    if not isinstance(reduce_only, bool):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    return {
        "execution_order_id": execution_order_id,
        "exchange_order_id": exchange_order_id,
        "symbol": symbol,
        "side": _SIDE_FROM_BYBIT[side_raw],
        "order_type": _ORDER_TYPE_FROM_BYBIT[order_type_raw],
        "quantity": _to_finite_decimal(item["qty"]),
        "filled_quantity": _to_finite_decimal(item["cumExecQty"]),
        "filled_value": _to_finite_decimal(item["cumExecValue"]),
        "reduce_only": reduce_only,
        "price": _to_optional_price_decimal(item.get("price")),
        "average_price": _to_optional_avg_price_decimal(item.get("avgPrice")),
        "reject_reason": _to_optional_reject_reason(item.get("rejectReason")),
        "remote_created_time_ms": _to_timestamp_ms(item["createdTime"], field="createdTime"),
        "remote_updated_time_ms": _to_timestamp_ms(item["updatedTime"], field="updatedTime"),
    }


def _interpret_realtime_item(
    item: object, *, execution_order_id: ExecutionOrderId, server_time_ms: int
) -> BybitRealtimeOrderFoundOpen | BybitOrderHistoryOrderFound:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    status_raw = item["orderStatus"] if "orderStatus" in item else None
    if status_raw in _OPEN_STATUS_FROM_BYBIT:
        fields = _common_fields(item, execution_order_id=execution_order_id)
        cancel_type = _to_optional_cancel_type(item.get("cancelType"))
        if cancel_type is not None:
            # Una orden ABIERTA nunca fue cancelada -- ver docstring de
            # BybitRealtimeOrderFoundOpen. Cualquier motivo real aquí es una
            # respuesta inconsistente y falla cerrado (sin normalizar).
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
        try:
            return BybitRealtimeOrderFoundOpen(
                remote_status=_OPEN_STATUS_FROM_BYBIT[status_raw],
                server_time_ms=server_time_ms,
                **fields,
            )
        except (TypeError, ValueError) as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error

    if status_raw in _CLOSED_STATUS_FROM_BYBIT:
        fields = _common_fields(item, execution_order_id=execution_order_id)
        cancel_type = _to_optional_cancel_type(item.get("cancelType"))
        try:
            return BybitOrderHistoryOrderFound(
                remote_status=_CLOSED_STATUS_FROM_BYBIT[status_raw],
                server_time_ms=server_time_ms,
                cancel_type=cancel_type,
                **fields,
            )
        except (TypeError, ValueError) as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error

    # Untriggered/Triggered/Deactivated/PartiallyFilledCanceled/cualquier
    # otro valor: estructuralmente imposible para una orden Phoenix
    # correlacionada por ExecutionOrderId (ver order_realtime_lookup_
    # contracts.py) -- Opción B, mismo tratamiento que ADR-012 D3.
    raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)


class BybitOrderRealtimeResponseInterpreter:
    def interpret(
        self, *, response: BybitResponse, execution_order_id: ExecutionOrderId
    ) -> BybitRealtimeOrderLookupResult | BybitOrderHistoryOrderFound:
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

        # Fail-closed ante paginación -- mismo principio que Order History
        # Lookup (Hito 3.86, §17): la documentación oficial no garantiza
        # nextPageCursor vacío para un filtro exacto por orderLinkId.
        if result.get("nextPageCursor"):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # Cardinalidad idéntica a 3.86: 0 -> NOT_FOUND (legítimo, nunca
        # error); >1 -> fail-closed (nunca se elige arbitrariamente el
        # primero); exactamente 1 -> interpretar y despachar por estado.
        if len(raw_list) == 0:
            return BybitRealtimeOrderNotFound()
        if len(raw_list) > 1:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        return _interpret_realtime_item(
            raw_list[0], execution_order_id=execution_order_id, server_time_ms=response.time_ms
        )
