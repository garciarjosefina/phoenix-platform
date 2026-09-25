from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.execution_identity_contracts import ExecutionOrderId

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}


def _require_non_empty_str(value, *, field: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be str, got: {type(value).__name__}")
    if not value or value.isspace():
        raise ValueError(f"{field} must not be empty or whitespace-only")


def _require_side(value, *, field: str) -> None:
    _require_non_empty_str(value, field=field)
    if value not in _VALID_SIDES:
        raise ValueError(f"{field} must be 'buy' or 'sell', got: {value!r}")


def _require_order_type(value, *, field: str) -> None:
    _require_non_empty_str(value, field=field)
    if value not in _VALID_ORDER_TYPES:
        raise ValueError(f"{field} must be 'market' or 'limit', got: {value!r}")


def _require_finite_positive_decimal(value, *, field: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field} must be Decimal, got: {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")
    if value <= 0:
        raise ValueError(f"{field} must be > 0, got: {value}")


@dataclass(frozen=True)
class ObservedOrderEconomics:
    """Value object neutral de economía observada -- Hito 3.91, ADR-014
    (Resolución del STOP de Hito 3.90, Decisión 1: Opción B).

    Representa EXCLUSIVAMENTE las siete dimensiones necesarias para que
    el Economic Comparator decida si una orden encontrada remotamente
    para `execution_order_id` describe la misma orden económica que
    Phoenix intentó enviar. Exchange-agnóstico por diseño: no nombra
    Bybit ni ningún otro exchange, y ambos resultados de lookup remoto
    (`BybitRealtimeOrderFoundOpen`, Hito 3.88; `BybitOrderHistoryOrderFound`,
    Hito 3.86) se proyectan mecánicamente a este mismo tipo -- el
    comparador nunca ve un tipo `Bybit*` (ADR-014, Resolución del STOP,
    Decisión 1).

    Campos EXACTOS, ninguno más (ADR-014, Contrato Conceptual de 3.91,
    punto A): `execution_order_id`, `symbol`, `side`, `order_type`,
    `quantity`, `price`, `reduce_only`. Deliberadamente SIN metadata ni
    evolución de la orden -- `exchange_order_id`, `filled_quantity`,
    `filled_value`, `average_price`, `remote_status`, `cancel_type`,
    `reject_reason`, `remote_created_time_ms`, `remote_updated_time_ms`,
    `server_time_ms` NO tienen campo aquí (ADR-014 D8): son evolución o
    metadato de observación, nunca la intención económica original.

    `quantity` y `price` son la cantidad y el precio ORIGINALES de la
    orden (ADR-014 D3/D4/F5) -- nunca remanente ni ejecución. `price` es
    `None` si y sólo si `order_type == "market"`, misma invariante cruzada
    que en `OrderSubmissionAttempted`/`BybitRealtimeOrderFoundOpen`/
    `BybitOrderHistoryOrderFound` (ADR-014 F6)."""

    execution_order_id: ExecutionOrderId
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None
    reduce_only: bool

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_positive_decimal(self.quantity, field="quantity")

        if self.price is not None:
            _require_finite_positive_decimal(self.price, field="price")
        if self.order_type == "limit" and self.price is None:
            raise ValueError("a 'limit' order must have price > 0, got price=None")
        if self.order_type == "market" and self.price is not None:
            raise ValueError("a 'market' order must have price=None")

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")


__all__ = ["ObservedOrderEconomics"]
