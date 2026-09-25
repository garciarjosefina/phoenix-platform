from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.execution_identity_contracts import ExecutionOrderId

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}


def _require_execution_order_id(value, *, field: str) -> None:
    if not isinstance(value, ExecutionOrderId):
        raise TypeError(f"{field} must be ExecutionOrderId, got: {type(value).__name__}")


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


def _require_bool(value, *, field: str) -> None:
    if not isinstance(value, bool):
        raise TypeError(f"{field} must be bool, got: {type(value).__name__}")


# ---------------------------------------------------------------------------
# Familia tipada de divergencia económica -- Hito 3.91, ADR-014 D12/D13.
# Deliberadamente propia, NO reutiliza el vocabulario `Divergence` de
# Reconciliation V1 (reconciliation_contracts.py, Hito 3.77): ese
# vocabulario está claveado por `order_id: str` (identidad Phoenix como
# string suelto) y responde otra pregunta (estado esperado de la cuenta
# contra snapshot completo, ADR-014 D13). Ninguna divergencia de identidad
# existe aquí -- una identidad cruzada es un defecto de programación
# (ADR-014 D9/D11/D19), representado por
# `EconomicComparisonPreconditionError`, nunca por un tipo de esta
# familia.
# ---------------------------------------------------------------------------

class EconomicDivergence:
    """Marcador base de toda divergencia económica del Economic Comparator.
    Nunca se instancia directamente -- sirve únicamente para
    isinstance/validación de tuplas homogéneas en
    `EconomicComparisonResult` (mismo patrón que `Divergence`,
    reconciliation_contracts.py, y que `LocalFact`/`RemoteFact`/
    `ObservedFact`, execution_ledger_event_contracts.py)."""


@dataclass(frozen=True)
class EconomicSymbolMismatch(EconomicDivergence):
    """`ObservedOrderEconomics` correlaciona por `execution_order_id`
    con `OrderSubmissionAttempted`, pero `symbol` difiere."""

    execution_order_id: ExecutionOrderId
    attempted_symbol: str
    observed_symbol: str

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_str(self.attempted_symbol, field="attempted_symbol")
        _require_str(self.observed_symbol, field="observed_symbol")


@dataclass(frozen=True)
class EconomicSideMismatch(EconomicDivergence):
    """Correlacionada por `execution_order_id`, pero `side` difiere."""

    execution_order_id: ExecutionOrderId
    attempted_side: str
    observed_side: str

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_side(self.attempted_side, field="attempted_side")
        _require_side(self.observed_side, field="observed_side")


@dataclass(frozen=True)
class EconomicOrderTypeMismatch(EconomicDivergence):
    """Correlacionada por `execution_order_id`, pero `order_type` difiere."""

    execution_order_id: ExecutionOrderId
    attempted_order_type: str
    observed_order_type: str

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_order_type(self.attempted_order_type, field="attempted_order_type")
        _require_order_type(self.observed_order_type, field="observed_order_type")


@dataclass(frozen=True)
class EconomicQuantityMismatch(EconomicDivergence):
    """Correlacionada por `execution_order_id`, pero `quantity` difiere --
    comparación exacta contra la cantidad ORIGINAL en ambos lados, nunca
    remanente ni ejecución (ADR-014 D3)."""

    execution_order_id: ExecutionOrderId
    attempted_quantity: Decimal
    observed_quantity: Decimal

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_finite_decimal(self.attempted_quantity, field="attempted_quantity")
        _require_finite_decimal(self.observed_quantity, field="observed_quantity")


@dataclass(frozen=True)
class EconomicPriceMismatch(EconomicDivergence):
    """Correlacionada por `execution_order_id`, pero `price` difiere --
    comparación exacta contra el precio ORIGINAL en ambos lados, nunca
    `average_price` (ADR-014 D4). Puede representar tanto un LIMIT con
    precio distinto como un mismatch de forma (`None` vs `Decimal`) --
    p. ej. cuando `order_type` también diverge entre MARKET y LIMIT."""

    execution_order_id: ExecutionOrderId
    attempted_price: Decimal | None
    observed_price: Decimal | None

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_optional_finite_decimal(self.attempted_price, field="attempted_price")
        _require_optional_finite_decimal(self.observed_price, field="observed_price")


@dataclass(frozen=True)
class EconomicReduceOnlyMismatch(EconomicDivergence):
    """Correlacionada por `execution_order_id`, pero `reduce_only` difiere.
    El lado `attempted` usa la semántica constante del adapter actual
    (`False`, ADR-014 D7) -- `OrderSubmissionAttempted` no porta este
    campo todavía."""

    execution_order_id: ExecutionOrderId
    attempted_reduce_only: bool
    observed_reduce_only: bool

    def __post_init__(self) -> None:
        _require_execution_order_id(self.execution_order_id, field="execution_order_id")
        _require_bool(self.attempted_reduce_only, field="attempted_reduce_only")
        _require_bool(self.observed_reduce_only, field="observed_reduce_only")


@dataclass(frozen=True)
class EconomicComparisonResult:
    """Resultado puro de comparar un `OrderSubmissionAttempted` contra un
    `ObservedOrderEconomics` (Hito 3.91, ADR-014 D12/D14). `divergences`
    preserva el orden determinista de evaluación de dimensiones (symbol,
    side, order_type, quantity, price, reduce_only, ADR-014 D2/D18) --
    nunca derivado de iteración de `set`/`dict`."""

    divergences: tuple[EconomicDivergence, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.divergences, tuple):
            raise TypeError(f"divergences must be tuple, got: {type(self.divergences).__name__}")
        for divergence in self.divergences:
            if not isinstance(divergence, EconomicDivergence):
                raise TypeError(
                    f"divergences must contain only EconomicDivergence instances, "
                    f"got: {type(divergence).__name__}"
                )

    @property
    def is_matched(self) -> bool:
        # Puramente derivado -- nunca un segundo estado que pueda
        # contradecir divergences (mismo patrón que
        # ReconciliationResult.is_in_sync, ADR-014 D12).
        return len(self.divergences) == 0


__all__ = [
    "EconomicDivergence",
    "EconomicSymbolMismatch",
    "EconomicSideMismatch",
    "EconomicOrderTypeMismatch",
    "EconomicQuantityMismatch",
    "EconomicPriceMismatch",
    "EconomicReduceOnlyMismatch",
    "EconomicComparisonResult",
]
