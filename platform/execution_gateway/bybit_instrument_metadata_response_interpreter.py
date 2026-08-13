from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

# Campos esenciales del instrumento: identidad, clasificación, y los dos
# bloques de filtros (priceFilter/lotSizeFilter) que documentan el ejemplo
# oficial de Bybit sin condición aparente para category=linear. leverageFilter
# se lee aparte vía .get() -- ver _interpret_leverage_filter, es accesorio
# (documentado ausente para category=spot; sin confirmación de presencia
# garantizada para todo instrumento linear, p.ej. pre-listing).
_REQUIRED_FIELDS = (
    "symbol",
    "baseCoin",
    "quoteCoin",
    "settleCoin",
    "status",
    "contractType",
    "priceFilter",
    "lotSizeFilter",
)

_PRICE_FILTER_REQUIRED_FIELDS = ("tickSize", "minPrice", "maxPrice")
_LOT_SIZE_FILTER_REQUIRED_FIELDS = ("qtyStep", "minOrderQty", "maxOrderQty")


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
    # Patrón genérico de campo accesorio (mismo que leverage/unrealized_pnl
    # en Positions/Wallet Balance Read): ausente o cadena vacía -> None;
    # "0" es un valor real preservado, no colapsado a None. Cualquier otro
    # valor sigue exigido a ser un Decimal finito válido.
    if value is None or value == "":
        return None
    return _to_finite_decimal(value)


def _interpret_price_filter(price_filter: object) -> tuple[Decimal, Decimal, Decimal]:
    if not isinstance(price_filter, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _PRICE_FILTER_REQUIRED_FIELDS:
        if field not in price_filter:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    tick_size = _to_finite_decimal(price_filter["tickSize"])
    min_price = _to_finite_decimal(price_filter["minPrice"])
    max_price = _to_finite_decimal(price_filter["maxPrice"])
    return tick_size, min_price, max_price


def _interpret_lot_size_filter(
    lot_size_filter: object,
) -> tuple[Decimal, Decimal, Decimal, Decimal | None, Decimal | None]:
    if not isinstance(lot_size_filter, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _LOT_SIZE_FILTER_REQUIRED_FIELDS:
        if field not in lot_size_filter:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    qty_step = _to_finite_decimal(lot_size_filter["qtyStep"])
    min_order_qty = _to_finite_decimal(lot_size_filter["minOrderQty"])
    max_order_qty = _to_finite_decimal(lot_size_filter["maxOrderQty"])
    # maxMktOrderQty/minNotionalValue: accesorios, ver
    # instrument_metadata_contracts.py para el razonamiento completo.
    max_market_order_qty = _to_optional_finite_decimal(lot_size_filter.get("maxMktOrderQty"))
    min_notional_value = _to_optional_finite_decimal(lot_size_filter.get("minNotionalValue"))
    return qty_step, min_order_qty, max_order_qty, max_market_order_qty, min_notional_value


def _interpret_leverage_filter(item: object) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    leverage_filter = item.get("leverageFilter") if isinstance(item, Mapping) else None
    if not isinstance(leverage_filter, Mapping):
        # Bloque ausente por completo, o de tipo inesperado -- se trata
        # igual que "sin metadata de leverage disponible" (accesorio, no
        # aborta el instrumento). No es lo mismo que un valor individual
        # malformado dentro de un bloque presente, que sí falla cerrado.
        return None, None, None
    min_leverage = _to_optional_finite_decimal(leverage_filter.get("minLeverage"))
    max_leverage = _to_optional_finite_decimal(leverage_filter.get("maxLeverage"))
    leverage_step = _to_optional_finite_decimal(leverage_filter.get("leverageStep"))
    return min_leverage, max_leverage, leverage_step


def _interpret_instrument_item(
    item: object, *, requested_symbol: str, server_time_ms: int
) -> ExecutionInstrumentMetadata:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    symbol = item["symbol"]
    if not isinstance(symbol, str) or not symbol or symbol.isspace():
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    # Identidad del instrumento -- punto crítico del Hito 3.73: el símbolo
    # devuelto debe coincidir EXACTAMENTE (comparación por valor de string,
    # no normalizada) con el solicitado. Si Bybit devolviera un símbolo
    # distinto (corrupción, bug de query, o comportamiento no documentado),
    # servir esa metadata como si fuera la del símbolo pedido sería un error
    # silencioso de identidad -- se falla cerrado en vez de confiar en el
    # símbolo remoto sin verificar.
    if symbol != requested_symbol:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    base_asset = item["baseCoin"]
    if not isinstance(base_asset, str) or not base_asset:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    quote_asset = item["quoteCoin"]
    if not isinstance(quote_asset, str) or not quote_asset:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    settlement_asset = item["settleCoin"]
    if not isinstance(settlement_asset, str) or not settlement_asset:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    # instrument_status/contract_type: preservados tal cual, sin traducir a
    # un enum cerrado -- ver instrument_metadata_contracts.py.
    instrument_status = item["status"]
    if not isinstance(instrument_status, str) or not instrument_status:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    contract_type = item["contractType"]
    if not isinstance(contract_type, str) or not contract_type:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    tick_size, min_price, max_price = _interpret_price_filter(item["priceFilter"])
    qty_step, min_order_qty, max_order_qty, max_market_order_qty, min_notional_value = (
        _interpret_lot_size_filter(item["lotSizeFilter"])
    )
    min_leverage, max_leverage, leverage_step = _interpret_leverage_filter(item)

    try:
        return ExecutionInstrumentMetadata(
            symbol=symbol,
            base_asset=base_asset,
            quote_asset=quote_asset,
            settlement_asset=settlement_asset,
            instrument_status=instrument_status,
            contract_type=contract_type,
            tick_size=tick_size,
            min_price=min_price,
            max_price=max_price,
            qty_step=qty_step,
            min_order_qty=min_order_qty,
            max_order_qty=max_order_qty,
            server_time_ms=server_time_ms,
            max_market_order_qty=max_market_order_qty,
            min_notional_value=min_notional_value,
            min_leverage=min_leverage,
            max_leverage=max_leverage,
            leverage_step=leverage_step,
        )
    except (TypeError, ValueError) as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


class BybitInstrumentMetadataResponseInterpreter:
    def interpret(self, *, response: BybitResponse, requested_symbol: str) -> ExecutionInstrumentMetadata:
        if not isinstance(response, BybitResponse):
            raise TypeError(f"response must be BybitResponse, got: {type(response).__name__}")
        if not isinstance(requested_symbol, str):
            raise TypeError(f"requested_symbol must be str, got: {type(requested_symbol).__name__}")
        if not requested_symbol or requested_symbol.isspace():
            raise ValueError("requested_symbol must not be empty or whitespace-only")

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

        # Fail-closed ante paginación -- a diferencia de wallet-balance
        # (donde nextPageCursor no existe en el esquema documentado),
        # /v5/market/instruments-info sí documenta paginación explícitamente
        # (mismo mecanismo que Positions/Open Orders Read). Aunque se
        # consulta por symbol exacto, la documentación no garantiza que el
        # cursor permanezca vacío en ese caso -- se trata cualquier valor
        # truthy como señal de paginación pendiente, nunca se sirve una
        # metadata potencialmente incompleta.
        if result.get("nextPageCursor"):
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # Identidad inequívoca: se consulta por symbol exacto, así que se
        # espera exactamente un instrumento. 0 elementos (símbolo inexistente
        # o typo) y >1 elementos (respuesta ambigua/corrupta) fallan cerrado
        # por igual -- nunca se toma "el primero" de una lista ambigua.
        if len(raw_list) != 1:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        # server_time_ms proviene exclusivamente del envelope remoto
        # (response.time_ms), nunca de un reloj local ni de un valor
        # inventado.
        return _interpret_instrument_item(
            raw_list[0], requested_symbol=requested_symbol, server_time_ms=response.time_ms
        )
