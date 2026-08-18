from dataclasses import dataclass
from decimal import Decimal

# Mismo vocabulario de dominio ya aceptado en positions_contracts.py /
# open_orders_contracts.py -- no se inventa un vocabulario nuevo para
# "lo que Phoenix espera" distinto del ya usado para "lo que Phoenix
# observa".
_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}


@dataclass(frozen=True)
class ExpectedExecutionScope:
    """Dónde ExpectedExecutionState es autoritativo.

    Un símbolo fuera de `symbols` es "desconocido" (Phoenix no afirma
    nada sobre él), nunca "se espera flat" -- esa distinción es la
    razón de ser de este contrato y se aplica en
    ExpectedExecutionState, no aquí.
    """

    symbols: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.symbols, tuple):
            raise TypeError(f"symbols must be tuple, got: {type(self.symbols).__name__}")

        seen: set[str] = set()
        for symbol in self.symbols:
            if not isinstance(symbol, str):
                raise TypeError(f"symbols must contain only str, got: {type(symbol).__name__}")
            if not symbol or symbol.isspace():
                raise ValueError("symbols must not contain empty or whitespace-only entries")
            if symbol in seen:
                raise ValueError(f"duplicate symbol in scope: {symbol!r}")
            seen.add(symbol)


@dataclass(frozen=True)
class ExpectedPosition:
    """Posición agregada que Phoenix afirma que debería existir para
    (symbol, side) dentro de un ExpectedExecutionScope.

    Deliberadamente sin entry_price/leverage/unrealized_pnl/margin/
    liquidation_price/positionIdx/bot_id/strategy_id -- (symbol, side)
    + quantity es la identidad y magnitud mínimas para reconciliación
    observacional agregada. No se afirma que alcance para actuar sobre
    posiciones hedge ni para atribuir ownership por bot.
    """

    symbol: str
    side: str
    quantity: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.side, str):
            raise TypeError(f"side must be str, got: {type(self.side).__name__}")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'buy' or 'sell', got: {self.side!r}")

        if not isinstance(self.quantity, Decimal):
            raise TypeError(f"quantity must be Decimal, got: {type(self.quantity).__name__}")
        if not self.quantity.is_finite():
            raise ValueError("quantity must be finite")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")


@dataclass(frozen=True)
class ExpectedOpenOrder:
    """Orden abierta que Phoenix afirma que debería existir, identificada
    por `order_id` -- identidad Phoenix (conceptualmente orderLinkId),
    nunca exchange_order_id: Phoenix no puede afirmar de antemano qué id
    asignará el exchange a una orden que todavía no existe remotamente.

    Deliberadamente sin exchange_order_id/filled_quantity/status/
    server_time/bot_id/strategy_id -- los campos dinámicos de progreso
    de ejecución no deben confundirse con una expectativa estática; su
    semántica se diseñará en el hito del Reconciliation Engine.

    `price` sigue la misma semántica ya aceptada en ExecutionOpenOrder
    (Hito 3.71, observacional): Decimal finito > 0 cuando está presente,
    `None` cuando no aplica -- deliberadamente SIN acoplar `price` a
    `order_type` (a diferencia de ExecutionRequest, el contrato de
    intención del write-side, que sí lo acopla). Se prefirió no inventar
    una semántica nueva más estricta que la ya aceptada para esta misma
    familia de contrato (orden abierta) -- ver docs/decisions.md.
    """

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    reduce_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.order_id, str):
            raise TypeError(f"order_id must be str, got: {type(self.order_id).__name__}")
        if not self.order_id or self.order_id.isspace():
            raise ValueError("order_id must not be empty or whitespace-only")

        if not isinstance(self.symbol, str):
            raise TypeError(f"symbol must be str, got: {type(self.symbol).__name__}")
        if not self.symbol or self.symbol.isspace():
            raise ValueError("symbol must not be empty or whitespace-only")

        if not isinstance(self.side, str):
            raise TypeError(f"side must be str, got: {type(self.side).__name__}")
        if self.side not in _VALID_SIDES:
            raise ValueError(f"side must be 'buy' or 'sell', got: {self.side!r}")

        if not isinstance(self.order_type, str):
            raise TypeError(f"order_type must be str, got: {type(self.order_type).__name__}")
        if self.order_type not in _VALID_ORDER_TYPES:
            raise ValueError(f"order_type must be 'market' or 'limit', got: {self.order_type!r}")

        if not isinstance(self.quantity, Decimal):
            raise TypeError(f"quantity must be Decimal, got: {type(self.quantity).__name__}")
        if not self.quantity.is_finite():
            raise ValueError("quantity must be finite")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got: {self.quantity}")

        if self.price is not None:
            if not isinstance(self.price, Decimal):
                raise TypeError(f"price must be Decimal or None, got: {type(self.price).__name__}")
            if not self.price.is_finite():
                raise ValueError("price must be finite")
            if self.price <= 0:
                raise ValueError(f"price must be > 0, got: {self.price}")

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")


@dataclass(frozen=True)
class ExpectedExecutionState:
    """Para `scope`, la totalidad del estado de ejecución que Phoenix
    afirma que debería existir.

    NO es la fuente primaria de verdad histórica -- es una PROYECCIÓN
    esperada. Una fuente canónica persistente/reconstruible (un futuro
    Execution Ledger) que la derive NO se implementa en este hito.

    Colecciones vacías dentro de un scope no vacío son válidas y
    significan ausencia esperada de esas entidades dentro del scope
    (ver ExpectedExecutionScope) -- nunca "no hay opinión". Un scope
    vacío (`symbols=()`) también es válido: mismo patrón ya aceptado en
    todo el read-side, donde una colección vacía (`positions=()`,
    `orders=()`, ausencia de una moneda en `currency_balances`) es un
    resultado legítimo, nunca un error -- aquí significa que Phoenix no
    reclama autoridad sobre ningún símbolo todavía.
    """

    scope: ExpectedExecutionScope
    positions: tuple[ExpectedPosition, ...]
    open_orders: tuple[ExpectedOpenOrder, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.scope, ExpectedExecutionScope):
            raise TypeError(
                f"scope must be ExpectedExecutionScope, got: {type(self.scope).__name__}"
            )

        if not isinstance(self.positions, tuple):
            raise TypeError(f"positions must be tuple, got: {type(self.positions).__name__}")
        for position in self.positions:
            if not isinstance(position, ExpectedPosition):
                raise TypeError(
                    f"positions must contain only ExpectedPosition, got: {type(position).__name__}"
                )

        if not isinstance(self.open_orders, tuple):
            raise TypeError(f"open_orders must be tuple, got: {type(self.open_orders).__name__}")
        for order in self.open_orders:
            if not isinstance(order, ExpectedOpenOrder):
                raise TypeError(
                    f"open_orders must contain only ExpectedOpenOrder, got: {type(order).__name__}"
                )

        symbols_in_scope = set(self.scope.symbols)

        seen_position_identities: set[tuple[str, str]] = set()
        for position in self.positions:
            if position.symbol not in symbols_in_scope:
                raise ValueError(
                    f"position symbol {position.symbol!r} is not in scope {self.scope.symbols!r}"
                )
            identity = (position.symbol, position.side)
            if identity in seen_position_identities:
                raise ValueError(f"duplicate position identity (symbol, side): {identity!r}")
            seen_position_identities.add(identity)

        seen_order_ids: set[str] = set()
        for order in self.open_orders:
            if order.symbol not in symbols_in_scope:
                raise ValueError(
                    f"open order symbol {order.symbol!r} is not in scope {self.scope.symbols!r}"
                )
            if order.order_id in seen_order_ids:
                raise ValueError(f"duplicate order_id: {order.order_id!r}")
            seen_order_ids.add(order.order_id)
