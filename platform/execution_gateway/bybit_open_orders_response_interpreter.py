from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.open_orders_contracts import ExecutionOpenOrder, OpenOrdersSnapshot

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

_SIDE_FROM_BYBIT = {"Buy": "buy", "Sell": "sell"}
_ORDER_TYPE_FROM_BYBIT = {"Market": "market", "Limit": "limit"}
# "Triggered" agregado tras la auditoría del Hito 3.71 (IMPORTANT-2): estado
# transitorio legítimo de una orden condicional (Untriggered -> Triggered ->
# New), observable en una carrera de lectura real. Ver _VALID_STATUSES en
# open_orders_contracts.py para el razonamiento completo.
_STATUS_FROM_BYBIT = {
    "New": "new",
    "PartiallyFilled": "partially_filled",
    "Untriggered": "untriggered",
    "Triggered": "triggered",
}

# orderLinkId y price se leen aparte vía .get() -- son opcionales (ver
# positions_contracts.py/ADR-002 para el mismo patrón aplicado a leverage/
# unrealisedPnl en el Hito 3.70). El resto identifica y dimensiona la orden.
_REQUIRED_FIELDS = ("orderId", "symbol", "side", "orderType", "qty", "cumExecQty", "orderStatus", "reduceOnly")


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
    # Específico de price -- no un patrón genérico reutilizable para
    # cualquier campo opcional. "" o ausente significan "sin precio
    # preestablecido"; "0" (comparado por valor tras parsear, cubre "0",
    # "0.0", "0.00", etc.) también, confirmado como respuesta legítima real
    # de Bybit para market orders, no sólo "" (IMPORTANT-1, auditoría del
    # Hito 3.71). No confundir con otros campos opcionales donde 0 sí es un
    # valor real y distinto de ausencia (p.ej. unrealisedPnl en Positions
    # Read, Hito 3.70) -- ese caso usa su propio helper, sin este atajo.
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


def _interpret_order_item(item: object) -> ExecutionOpenOrder:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    exchange_order_id = item["orderId"]
    if not isinstance(exchange_order_id, str) or not exchange_order_id or exchange_order_id.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    # orderLinkId ausente o "" -> None (identidad de dominio desconocida,
    # posible orden huérfana). Nunca se inventa ni se oculta la orden.
    order_id = _to_optional_non_empty_str(item.get("orderLinkId"))

    symbol = item["symbol"]
    if not isinstance(symbol, str):
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
    if status_raw not in _STATUS_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    status = _STATUS_FROM_BYBIT[status_raw]

    reduce_only = item["reduceOnly"]
    if not isinstance(reduce_only, bool):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    quantity = _to_finite_decimal(item["qty"])
    filled_quantity = _to_finite_decimal(item["cumExecQty"])
    # price ausente/""/"0" se trata como None -- ver _to_optional_price_decimal.
    price = _to_optional_price_decimal(item.get("price"))

    try:
        return ExecutionOpenOrder(
            exchange_order_id=exchange_order_id,
            order_id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            filled_quantity=filled_quantity,
            status=status,
            reduce_only=reduce_only,
        )
    except (TypeError, ValueError) as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


class BybitOpenOrdersResponseInterpreter:
    def interpret(self, *, response: BybitResponse) -> OpenOrdersSnapshot:
        if not isinstance(response, BybitResponse):
            raise TypeError(f"response must be BybitResponse, got: {type(response).__name__}")

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

        # Fail-closed ante paginación -- lección directa del Hito 3.70
        # (IMPORTANT-1 de su auditoría): nunca se sirve un snapshot
        # silenciosamente truncado. Ausencia de la clave o cadena vacía se
        # tratan igual (sin señal de paginación pendiente); cualquier otro
        # valor truthy -- incluido whitespace -- falla cerrado. No se
        # implementa el follow-up de cursor en este hito.
        if result.get("nextPageCursor"):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # A diferencia de Positions Read, no se filtra ningún ítem: el
        # propio endpoint /v5/order/realtime ya sólo devuelve órdenes
        # abiertas/parcialmente llenas -- cada entrada de `list` es una
        # ExecutionOpenOrder legítima. Sin deduplicación por atributos
        # económicos: la identidad es orderId/orderLinkId, nunca
        # symbol/side/price.
        orders = tuple(_interpret_order_item(item) for item in raw_list)
        return OpenOrdersSnapshot(orders=orders, server_time_ms=response.time_ms)
