from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.execution_identity_contracts import ExecutionOrderId

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}
# Hito 3.86 / ADR-012 D1-D3: de los seis estados "closed" que documenta el
# enum oficial de Bybit (Filled/Cancelled/Rejected/Deactivated/
# PartiallyFilledCanceled/Triggered), sólo estos tres son alcanzables por una
# orden Phoenix (category=linear, market/limit, sin condicionales/TP-SL/OCO).
# Deactivated (sólo condicionales), PartiallyFilledCanceled (sólo spot) y
# Triggered (transitorio, ya tratado como abierto desde el Hito 3.71) son
# estructuralmente imposibles para el scope actual y se rechazan en el
# interpreter -- ver bybit_order_history_response_interpreter.py.
_VALID_REMOTE_STATUSES = {"filled", "cancelled", "rejected"}


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


def _require_finite_non_negative_decimal(value, *, field: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field} must be Decimal, got: {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")
    if value < 0:
        raise ValueError(f"{field} must be >= 0, got: {value}")


def _require_non_negative_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{field} must be >= 0, got: {value}")


class BybitOrderHistoryLookupResult:
    """Marcador no instanciable, base de todo resultado de una consulta a
    `GET /v5/order/history` filtrada por `orderLinkId`.

    Existen exactamente dos subtipos concretos, nunca un tercer estado ni un
    campo de status libre: `BybitOrderHistoryOrderFound` /
    `BybitOrderHistoryOrderNotFound`. Este hito (3.86) implementa
    exclusivamente la primitiva de lectura -- NO construye eventos del
    Execution Ledger (`OrderObservedClosed`, ADR-012) ni realiza ninguna
    acción de recovery; ambos quedan para hitos posteriores.
    """


@dataclass(frozen=True)
class BybitOrderHistoryOrderFound(BybitOrderHistoryLookupResult):
    """Bybit devolvió, dentro de `/v5/order/history` filtrado por
    `orderLinkId`, EXACTAMENTE una orden cuyo `orderLinkId` coincide byte a
    byte con el `ExecutionOrderId` solicitado (correlación verificada por el
    interpreter, nunca asumida por haber sido el filtro de la query).

    Preserva los 17 campos que ADR-012 D16 identificó como necesarios para
    construir en el futuro un `OrderObservedClosed` -- 16 STABLE REMOTE FACT
    CONTENT (todo lo que Bybit afirma sobre la orden) + 1 OBSERVATION
    METADATA (`server_time_ms`, el instante de ESTA consulta, no una
    propiedad de la orden; ver ADR-012, "Corrección post-reauditoría de
    D12"). Este dataclass NO es `OrderObservedClosed`: no hereda de
    `ObservedFact` ni participa del envelope del Ledger -- es
    exclusivamente el resultado tipado de la lectura, listo para que un hito
    futuro lo traduzca sin tener que reinterpretar la respuesta cruda de
    Bybit.

    "Filled" no es un fill ledger: `filled_quantity`/`filled_value`/
    `average_price` son los agregados acumulados que Bybit reporta A NIVEL
    DE ORDEN (`cumExecQty`/`cumExecValue`/`avgPrice`), nunca ejecuciones
    individuales, fees por fill, ni atribución de trades (ADR-012 D4).

    `remote_updated_time_ms` es el `updatedTime` que Bybit documenta -- NO
    se interpreta como "tiempo de fill" ni "tiempo de cierre": Bybit no lo
    garantiza como tal (ADR-012 D7).
    """

    execution_order_id: ExecutionOrderId
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    filled_value: Decimal
    remote_status: str
    reduce_only: bool
    server_time_ms: int
    remote_created_time_ms: int
    remote_updated_time_ms: int
    price: Decimal | None = None
    average_price: Decimal | None = None
    cancel_type: str | None = None
    reject_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.exchange_order_id, field="exchange_order_id")
        _require_non_empty_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_positive_decimal(self.quantity, field="quantity")
        _require_finite_non_negative_decimal(self.filled_quantity, field="filled_quantity")
        if self.filled_quantity > self.quantity:
            raise ValueError(
                f"filled_quantity must be <= quantity, "
                f"got: filled_quantity={self.filled_quantity}, quantity={self.quantity}"
            )
        _require_finite_non_negative_decimal(self.filled_value, field="filled_value")

        _require_non_empty_str(self.remote_status, field="remote_status")
        if self.remote_status not in _VALID_REMOTE_STATUSES:
            raise ValueError(
                f"remote_status must be one of {sorted(_VALID_REMOTE_STATUSES)}, "
                f"got: {self.remote_status!r}"
            )

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")

        _require_non_negative_int(self.server_time_ms, field="server_time_ms")
        _require_non_negative_int(self.remote_created_time_ms, field="remote_created_time_ms")
        _require_non_negative_int(self.remote_updated_time_ms, field="remote_updated_time_ms")
        if self.remote_updated_time_ms < self.remote_created_time_ms:
            raise ValueError(
                f"remote_updated_time_ms must be >= remote_created_time_ms, "
                f"got: updated={self.remote_updated_time_ms}, created={self.remote_created_time_ms}"
            )

        if self.price is not None:
            _require_finite_positive_decimal(self.price, field="price")
        if self.order_type == "limit" and self.price is None:
            raise ValueError("a 'limit' order must have price > 0, got price=None")
        if self.order_type == "market" and self.price is not None:
            raise ValueError("a 'market' order must have price=None")

        if self.average_price is not None:
            _require_finite_positive_decimal(self.average_price, field="average_price")
        if (self.average_price is None) != (self.filled_quantity == 0):
            raise ValueError(
                "average_price must be None if and only if filled_quantity == 0, "
                f"got: average_price={self.average_price!r}, filled_quantity={self.filled_quantity}"
            )
        if (self.filled_value == 0) != (self.filled_quantity == 0):
            raise ValueError(
                "filled_value must be 0 if and only if filled_quantity == 0, "
                f"got: filled_value={self.filled_value}, filled_quantity={self.filled_quantity}"
            )

        if self.cancel_type is not None:
            _require_non_empty_str(self.cancel_type, field="cancel_type")
        if self.remote_status != "cancelled" and self.cancel_type is not None:
            raise ValueError(
                f"cancel_type must be None when remote_status != 'cancelled', "
                f"got: remote_status={self.remote_status!r}, cancel_type={self.cancel_type!r}"
            )

        if self.reject_reason is not None:
            _require_non_empty_str(self.reject_reason, field="reject_reason")

        # Invariantes cruzadas ADR-012 D3 -- el estado remoto es congruente
        # con la magnitud efectivamente ejecutada. "Cancelled" con
        # filled_quantity == quantity sería, por definición de Bybit,
        # "Filled" -- una respuesta real que afirmara ambas cosas a la vez
        # es contradictoria y se rechaza en vez de silenciarse.
        if self.remote_status == "filled" and self.filled_quantity != self.quantity:
            raise ValueError(
                "remote_status == 'filled' requires filled_quantity == quantity, "
                f"got: filled_quantity={self.filled_quantity}, quantity={self.quantity}"
            )
        if self.remote_status == "rejected" and self.filled_quantity != 0:
            raise ValueError(
                "remote_status == 'rejected' requires filled_quantity == 0, "
                f"got: filled_quantity={self.filled_quantity}"
            )
        if self.remote_status == "cancelled" and self.filled_quantity >= self.quantity:
            raise ValueError(
                "remote_status == 'cancelled' requires filled_quantity < quantity "
                "(MENOR-2, ADR-012: invariante conservadora pendiente de validación empírica "
                "en Bybit Demo), "
                f"got: filled_quantity={self.filled_quantity}, quantity={self.quantity}"
            )


@dataclass(frozen=True)
class BybitOrderHistoryOrderNotFound(BybitOrderHistoryLookupResult):
    """`/v5/order/history` no devolvió ninguna orden correlacionada con el
    `ExecutionOrderId` solicitado -- exclusivamente eso.

    NO significa, y NO debe interpretarse como:
      - que Bybit nunca recibió la orden;
      - que la orden fue rechazada;
      - que es seguro reenviar la orden con la misma o distinta identidad.

    `/v5/order/history` tiene retención asimétrica y puede aún no reflejar
    una orden reciente ("As order creation/cancellation is asynchronous, the
    data returned from this endpoint may delay", documentación oficial); una
    ausencia aquí es evidencia negativa débil, nunca una prueba de ausencia.
    Cualquier decisión sobre qué hacer ante este resultado (reintentar,
    escalar, esperar) es responsabilidad exclusiva de un futuro recovery
    worker -- fuera de alcance del Hito 3.86 (ver ADR-012, Resolución del
    STOP, puntos 5 y 6)."""


__all__ = [
    "BybitOrderHistoryLookupResult",
    "BybitOrderHistoryOrderFound",
    "BybitOrderHistoryOrderNotFound",
]
