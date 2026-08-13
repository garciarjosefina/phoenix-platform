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
#
# Clasificación explícita contra evidencia oficial (Corrección post-3.72,
# auditoría adversarial independiente -- IMPORTANTE-1):
#
#   totalEquity              -> C (documentación insuficiente)
#   totalWalletBalance       -> C (documentación insuficiente)
#   totalAvailableBalance    -> C (documentación insuficiente)
#   totalInitialMargin       -> C (documentación insuficiente)
#   totalMaintenanceMargin   -> C (documentación insuficiente)
#
# La documentación oficial de Bybit V5 contiene una única nota, genérica y
# aplicada por igual a los cinco ("All account wide fields are not
# applicable to isolated margin"), ubicada como bullet final tras la
# descripción de accountMMRate -- NO como anotación individual de ningún
# campo. Esa nota NO especifica qué representación toma cada campo cuando
# "no aplica" (cadena vacía, "0", clave ausente, u otra cosa): no hay
# evidencia field-specific que permita distinguir un campo de otro, ni que
# permita inferir con confianza el valor concreto devuelto.
#
# Por contraste, este mismo endpoint SÍ documenta explícitamente "" para
# otro conjunto de campos bajo otro modo (totalOrderIM/totalPositionIM/
# totalPositionMM a nivel moneda, bajo portfolio margin: "For portfolio
# margin mode, it returns \"\""), lo que confirma que Bybit sabe declarar
# ese comportamiento cuando quiere -- y explícitamente no lo hizo para
# estos cinco campos de cuenta bajo isolated margin.
#
# Decisión: ante documentación insuficiente para relajar selectivamente
# alguno de los cinco, se mantienen los cinco esenciales y fail-closed
# (ninguno se convierte a Optional). Relajarlos sin evidencia field-specific
# repetiría exactamente el patrón que motivó las correcciones post-3.70
# (leverage="") y post-3.71 (price="0"): una suposición no confirmada sobre
# el dato remoto. La incertidumbre queda registrada aquí y en ADR-002 en
# vez de resuelta por conveniencia. Si una cuenta Demo real bajo isolated
# margin llega a producir un `BybitResponseProcessingError` observable en
# producción, eso es la señal correcta -- evidencia real, no supuesta -- de
# que corresponde revisar esta clasificación con datos concretos.
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
        # /v5/order/realtime). El ejemplo oficial de respuesta muestra
        # `result.list` con un único objeto de cuenta para un `accountType`
        # consultado, pero la documentación no declara explícitamente la
        # cardinalidad como garantía formal.
        #
        # `len(raw_list) != 1` es, por lo tanto, una invariante conservadora
        # de Phoenix para accountType=UNIFIED -- no una cardinalidad
        # explícitamente garantizada por la documentación oficial consultada
        # (corrección post-3.72, MENOR-5: el comentario original presentaba
        # esto como si fuera un hecho documentado por Bybit). Se mantiene
        # fail-closed deliberadamente: 0 o >1 elementos es una forma remota
        # no modelada por este hito, y se prefiere rechazar explícitamente
        # antes que adivinar cuál elemento usar o asumir sin evidencia que
        # esa forma nunca ocurre.
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
