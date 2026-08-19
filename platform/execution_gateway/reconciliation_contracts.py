from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.exchange_state_contracts import ObservationWindow

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}


def _require_str(value, *, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be str, got: {type(value).__name__}")
    if not value or value.isspace():
        raise ValueError(f"{field} must not be empty or whitespace-only")


def _require_side(value, *, field: str) -> None:
    _require_str(value, field=field)
    if value not in _VALID_SIDES:
        raise ValueError(f"{field} must be 'buy' or 'sell', got: {value!r}")


def _require_order_type(value, *, field: str) -> None:
    _require_str(value, field=field)
    if value not in _VALID_ORDER_TYPES:
        raise ValueError(f"{field} must be 'market' or 'limit', got: {value!r}")


def _require_finite_decimal(value, *, field: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field} must be Decimal, got: {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")


def _require_optional_finite_decimal(value, *, field: str) -> None:
    if value is not None:
        _require_finite_decimal(value, field=field)


class Divergence:
    """Marcador base de toda divergencia de reconciliación. Nunca se
    instancia directamente -- sirve únicamente para isinstance/validación
    de tuplas homogéneas en ReconciliationResult."""


# ---------------------------------------------------------------------------
# Posiciones -- identidad (symbol, side). Sólo puede existir divergencia de
# cantidad una vez matched, porque symbol/side SON la identidad: no puede
# haber "PositionSymbolMismatch" ni "PositionSideMismatch".
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MissingExpectedPosition(Divergence):
    """Existe ExpectedPosition(symbol, side) pero ninguna posición
    observada con esa identidad."""

    symbol: str
    side: str
    expected_quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_finite_decimal(self.expected_quantity, field="expected_quantity")


@dataclass(frozen=True)
class UnexpectedExchangePosition(Divergence):
    """Existe una posición observada (symbol, side) dentro del scope, pero
    ninguna ExpectedPosition con esa identidad."""

    symbol: str
    side: str
    observed_quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_finite_decimal(self.observed_quantity, field="observed_quantity")


@dataclass(frozen=True)
class PositionQuantityMismatch(Divergence):
    """Misma identidad (symbol, side) en expected y observed, pero
    quantity difiere -- comparación exacta de Decimal, sin tolerancias."""

    symbol: str
    side: str
    expected_quantity: Decimal
    observed_quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_finite_decimal(self.expected_quantity, field="expected_quantity")
        _require_finite_decimal(self.observed_quantity, field="observed_quantity")


# ---------------------------------------------------------------------------
# Órdenes -- identidad = order_id Phoenix (ExpectedOpenOrder.order_id <->
# ExecutionOpenOrder.order_id). exchange_order_id NUNCA participa como
# fallback de identidad -- ver UnattributedExchangeOpenOrder, la única
# clase que lo transporta, precisamente porque no hay order_id Phoenix.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MissingExpectedOpenOrder(Divergence):
    """Existe ExpectedOpenOrder(order_id) pero ninguna orden observada con
    ese order_id Phoenix."""

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_decimal(self.quantity, field="quantity")


@dataclass(frozen=True)
class UnexpectedExchangeOpenOrder(Divergence):
    """Orden observada con order_id Phoenix presente, dentro del scope,
    pero ese order_id no corresponde a ningún ExpectedOpenOrder."""

    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_decimal(self.quantity, field="quantity")


@dataclass(frozen=True)
class UnattributedExchangeOpenOrder(Divergence):
    """Orden observada sin order_id Phoenix (order_id is None), dentro del
    scope -- observada por el exchange sin identidad Phoenix atribuible.
    Transporta exchange_order_id porque es el único identificador
    disponible; nunca se sustituye por un order_id inventado."""

    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.exchange_order_id, field="exchange_order_id")
        _require_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_decimal(self.quantity, field="quantity")


@dataclass(frozen=True)
class OrderSymbolMismatch(Divergence):
    """Orden matched por order_id Phoenix, pero symbol difiere."""

    order_id: str
    expected_symbol: str
    observed_symbol: str

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_str(self.expected_symbol, field="expected_symbol")
        _require_str(self.observed_symbol, field="observed_symbol")


@dataclass(frozen=True)
class OrderSideMismatch(Divergence):
    """Orden matched por order_id Phoenix, pero side difiere."""

    order_id: str
    expected_side: str
    observed_side: str

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_side(self.expected_side, field="expected_side")
        _require_side(self.observed_side, field="observed_side")


@dataclass(frozen=True)
class OrderQuantityMismatch(Divergence):
    """Orden matched por order_id Phoenix, pero quantity difiere --
    comparación exacta contra expected.quantity, nunca remaining
    (quantity - filled_quantity)."""

    order_id: str
    expected_quantity: Decimal
    observed_quantity: Decimal

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_finite_decimal(self.expected_quantity, field="expected_quantity")
        _require_finite_decimal(self.observed_quantity, field="observed_quantity")


@dataclass(frozen=True)
class OrderTypeMismatch(Divergence):
    """Orden matched por order_id Phoenix, pero order_type difiere."""

    order_id: str
    expected_order_type: str
    observed_order_type: str

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_order_type(self.expected_order_type, field="expected_order_type")
        _require_order_type(self.observed_order_type, field="observed_order_type")


@dataclass(frozen=True)
class OrderPriceMismatch(Divergence):
    """Orden matched por order_id Phoenix, expected.order_type == 'limit',
    y price difiere (comparación exacta) u observed.price is None.
    Nunca se emite para una orden esperada 'market' -- V1 no reconcilia
    price de mercado (ver reconciliation_engine.py)."""

    order_id: str
    expected_price: Decimal | None
    observed_price: Decimal | None

    def __post_init__(self) -> None:
        _require_str(self.order_id, field="order_id")
        _require_optional_finite_decimal(self.expected_price, field="expected_price")
        _require_optional_finite_decimal(self.observed_price, field="observed_price")


@dataclass(frozen=True)
class ReconciliationResult:
    """Resultado puro de reconciliar un ExpectedExecutionState contra un
    ExchangeStateSnapshot. `observation_window` se preserva tal cual del
    snapshot observado -- sólo para que el caller sepa de qué ventana
    provienen estas divergencias; V1 no decide freshness/staleness."""

    divergences: tuple[Divergence, ...]
    observation_window: ObservationWindow

    def __post_init__(self) -> None:
        if not isinstance(self.divergences, tuple):
            raise TypeError(f"divergences must be tuple, got: {type(self.divergences).__name__}")
        for divergence in self.divergences:
            if not isinstance(divergence, Divergence):
                raise TypeError(
                    f"divergences must contain only Divergence instances, "
                    f"got: {type(divergence).__name__}"
                )

        if not isinstance(self.observation_window, ObservationWindow):
            raise TypeError(
                f"observation_window must be ObservationWindow, "
                f"got: {type(self.observation_window).__name__}"
            )

    @property
    def is_in_sync(self) -> bool:
        # Puramente derivado -- nunca un segundo estado que pueda
        # contradecir divergences.
        return len(self.divergences) == 0
