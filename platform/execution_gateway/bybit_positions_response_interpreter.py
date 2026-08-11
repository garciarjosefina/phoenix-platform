from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.positions_contracts import ExecutionPosition, PositionsSnapshot

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

# side="Buy"/"Sell" es la única distinción que necesitamos para representar
# hedge mode: Bybit modela las dos piernas de una posición hedged del mismo
# symbol como dos entradas de `list` con size>0 y side opuesto. No se necesita
# `positionIdx` -- (symbol, side) ya distingue ambas piernas sin colapsarlas.
_SIDE_FROM_BYBIT = {"Buy": "buy", "Sell": "sell"}

# Sólo los campos que identifican y dimensionan la posición son esenciales.
# leverage/unrealisedPnl son accesorios (IMPORTANT-2, auditoría Hito 3.70):
# ausentes o vacíos en una respuesta válida no invalidan la fila completa.
_REQUIRED_FIELDS = ("symbol", "side", "size", "avgPrice")


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


def _to_optional_finite_decimal(value: object) -> Decimal | None:
    # Ausente ("None", clave inexistente vía .get()) o cadena vacía se
    # tratan igual: el exchange no reportó el dato para esta fila. Cualquier
    # otro valor sigue exigido a ser un Decimal finito válido -- nunca se
    # acepta en silencio si está malformado.
    if value is None or value == "":
        return None
    return _to_finite_decimal(value)


def _interpret_position_item(item: object) -> ExecutionPosition | None:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    quantity = _to_finite_decimal(item["size"])
    if quantity < 0:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    if quantity == 0:
        # Tamaño cero == sin posición para este symbol/side (placeholder de
        # Bybit, frecuente cuando side="None"). No es un error: se excluye
        # del snapshot en lugar de modelarse como una "posición" con size 0.
        return None

    symbol = item["symbol"]
    if not isinstance(symbol, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    side_raw = item["side"]
    if side_raw not in _SIDE_FROM_BYBIT:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    side = _SIDE_FROM_BYBIT[side_raw]

    # avgPrice sigue siendo esencial y obligatorio (ver positions_contracts.py
    # para el razonamiento de por qué se exige > 0 sin excepción).
    entry_price = _to_finite_decimal(item["avgPrice"])
    leverage = _to_optional_finite_decimal(item.get("leverage"))
    unrealized_pnl = _to_optional_finite_decimal(item.get("unrealisedPnl"))

    try:
        return ExecutionPosition(
            symbol=symbol,
            side=side,
            quantity=quantity,
            entry_price=entry_price,
            leverage=leverage,
            unrealized_pnl=unrealized_pnl,
        )
    except (TypeError, ValueError) as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


class BybitPositionsResponseInterpreter:
    def interpret(self, *, response: BybitResponse) -> PositionsSnapshot:
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

        # Fail-closed ante paginación (IMPORTANT-1, auditoría Hito 3.70): un
        # nextPageCursor no vacío significa que Bybit tiene más resultados de
        # los que esta consulta de página única (limit=200) solicitó. Devolver
        # el snapshot igual sería mentir por omisión -- nada distinguiría "no
        # hay más posiciones" de "hay más y no se pidieron". Se prefiere
        # fallar explícitamente antes que servir un snapshot truncado como si
        # fuera completo. Ausencia de la clave o cadena vacía se tratan igual:
        # sin señal de paginación pendiente. Cualquier otro valor truthy --
        # incluido whitespace -- se trata como señal de paginación pendiente.
        # No se implementa el follow-up de cursor en este hito (deuda
        # documentada explícitamente en ADR-002).
        if result.get("nextPageCursor"):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        positions = tuple(
            position
            for position in (_interpret_position_item(item) for item in raw_list)
            if position is not None
        )
        return PositionsSnapshot(positions=positions, server_time_ms=response.time_ms)
