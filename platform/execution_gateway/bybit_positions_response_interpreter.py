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

_REQUIRED_FIELDS = ("symbol", "side", "size", "avgPrice", "leverage", "unrealisedPnl")


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

    entry_price = _to_finite_decimal(item["avgPrice"])
    leverage = _to_finite_decimal(item["leverage"])
    unrealized_pnl = _to_finite_decimal(item["unrealisedPnl"])

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

        positions = tuple(
            position
            for position in (_interpret_position_item(item) for item in raw_list)
            if position is not None
        )
        return PositionsSnapshot(positions=positions, server_time_ms=response.time_ms)
