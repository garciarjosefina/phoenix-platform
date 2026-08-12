from collections.abc import Mapping
from decimal import Decimal, InvalidOperation

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.wallet_balance_contracts import ExecutionCurrencyBalance, WalletBalanceSnapshot

_PROCESSING_ERROR_MESSAGE = "Bybit response could not be processed"

# Campos que identifican y dimensionan la cuenta: los cinco totales elegidos
# (ver wallet_balance_contracts.py) son esenciales -- son la razón de ser de
# este hito. `coin` (la lista anidada) también es esencial estructuralmente:
# sin ella no hay forma de construir currency_balances.
_ACCOUNT_REQUIRED_FIELDS = (
    "totalEquity",
    "totalWalletBalance",
    "totalAvailableBalance",
    "totalInitialMargin",
    "totalMaintenanceMargin",
    "coin",
)

# A nivel de moneda, sólo coin/walletBalance/equity son esenciales.
# unrealisedPnl/usdValue son accesorios (ver ExecutionCurrencyBalance).
_CURRENCY_REQUIRED_FIELDS = ("coin", "walletBalance", "equity")


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
    # Mismo patrón que leverage/unrealized_pnl en
    # bybit_positions_response_interpreter.py: ausente o cadena vacía ->
    # None; "0" es un valor real (P&L nulo / valor USD nulo), no se colapsa
    # a None. Cualquier otro valor sigue exigido a ser un Decimal finito
    # válido -- nunca se acepta en silencio si está malformado.
    if value is None or value == "":
        return None
    return _to_finite_decimal(value)


def _interpret_currency_item(item: object) -> ExecutionCurrencyBalance:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _CURRENCY_REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    coin = item["coin"]
    if not isinstance(coin, str):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    wallet_balance = _to_finite_decimal(item["walletBalance"])
    equity = _to_finite_decimal(item["equity"])
    unrealized_pnl = _to_optional_finite_decimal(item.get("unrealisedPnl"))
    usd_value = _to_optional_finite_decimal(item.get("usdValue"))

    try:
        return ExecutionCurrencyBalance(
            coin=coin,
            wallet_balance=wallet_balance,
            equity=equity,
            unrealized_pnl=unrealized_pnl,
            usd_value=usd_value,
        )
    except (TypeError, ValueError) as error:
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error


def _interpret_account_item(item: object) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, tuple]:
    if not isinstance(item, Mapping):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    for field in _ACCOUNT_REQUIRED_FIELDS:
        if field not in item:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

    total_equity = _to_finite_decimal(item["totalEquity"])
    total_wallet_balance = _to_finite_decimal(item["totalWalletBalance"])
    total_available_balance = _to_finite_decimal(item["totalAvailableBalance"])
    total_initial_margin = _to_finite_decimal(item["totalInitialMargin"])
    total_maintenance_margin = _to_finite_decimal(item["totalMaintenanceMargin"])

    raw_coins = item["coin"]
    if not isinstance(raw_coins, tuple):
        raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)
    currency_balances = tuple(_interpret_currency_item(coin_item) for coin_item in raw_coins)

    return (
        total_equity,
        total_wallet_balance,
        total_available_balance,
        total_initial_margin,
        total_maintenance_margin,
        currency_balances,
    )


class BybitWalletBalanceResponseInterpreter:
    def interpret(self, *, response: BybitResponse) -> WalletBalanceSnapshot:
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

        # /v5/account/wallet-balance no pagina (sin nextPageCursor en su
        # esquema documentado, a diferencia de /v5/position/list y
        # /v5/order/realtime): `result.list` envuelve exactamente un objeto
        # de cuenta por cada `accountType` consultado. Como este hito
        # consulta un único accountType (UNIFIED, fijo), se espera
        # exactamente un elemento -- 0 o >1 es una forma remota no modelada
        # que se rechaza en vez de adivinar cuál elemento usar.
        if len(raw_list) != 1:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE)

        (
            total_equity,
            total_wallet_balance,
            total_available_balance,
            total_initial_margin,
            total_maintenance_margin,
            currency_balances,
        ) = _interpret_account_item(raw_list[0])

        try:
            return WalletBalanceSnapshot(
                total_equity=total_equity,
                total_wallet_balance=total_wallet_balance,
                total_available_balance=total_available_balance,
                total_initial_margin=total_initial_margin,
                total_maintenance_margin=total_maintenance_margin,
                currency_balances=currency_balances,
                server_time_ms=response.time_ms,
            )
        except (TypeError, ValueError) as error:
            raise BybitResponseProcessingError(message=_PROCESSING_ERROR_MESSAGE) from error
