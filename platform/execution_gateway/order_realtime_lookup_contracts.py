from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}
# Hito 3.88: taxonomía DELIBERADAMENTE más estrecha que la de
# OpenOrdersReader/open_orders_contracts.py (Hito 3.71: {new,
# partially_filled, untriggered, triggered}). Aquella lee el snapshot
# COMPLETO de la cuenta -- cualquier orden abierta, de cualquier origen,
# incluidas condicionales (Untriggered/Triggered). Ésta filtra por un
# ExecutionOrderId acuñado por Phoenix, que sólo se adjunta a órdenes
# market/limit no condicionales (ExecutionRequest/bybit_gateway.py no
# admiten triggerPrice/stopOrderType). Una respuesta correlacionada con
# orderStatus=Untriggered/Triggered sería, para ESTA identidad, tan
# estructuralmente imposible como Deactivated lo es en ADR-012 D1/F2 --
# se rechaza en el interpreter en vez de ampliarse por comodidad.
_VALID_OPEN_STATUSES = {"new", "partially_filled"}


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


class BybitRealtimeOrderLookupResult:
    """Marcador no instanciable, base de todo resultado de una consulta a
    `GET /v5/order/realtime` filtrada por `orderLinkId`.

    A diferencia de `BybitOrderHistoryLookupResult` (Hito 3.86, sólo dos
    subtipos), esta familia tiene DOS ramas concretas propias --
    `BybitRealtimeOrderFoundOpen` / `BybitRealtimeOrderNotFound` -- MÁS un
    tercer resultado posible que NO es un subtipo de este marcador:
    `BybitOrderHistoryOrderFound` (reutilizado tal cual de
    `order_history_lookup_contracts.py`, Hito 3.86, sin ninguna
    modificación). Razón: documentación oficial de Bybit confirma que
    `openOnly` se IGNORA al filtrar por `orderId`/`orderLinkId`
    ("`openOnly` param will be ignored when query by orderId or
    orderLinkId") -- una consulta por identidad puede devolver
    legítimamente una fila CERRADA (dentro de la caché volátil de
    cerradas que ADR-012 F4 ya documentó para este mismo endpoint). El
    hecho de una orden cerrada no depende de qué endpoint lo reportó, así
    que se representa con el MISMO contrato ya validado y aceptado en
    3.86 -- nunca colapsado en `BybitRealtimeOrderNotFound` (perdería
    evidencia útil) ni forzado en `BybitRealtimeOrderFoundOpen` (violaría
    sus propias invariantes de estado abierto).

    El tipo de retorno real de la primitiva de lookup es la unión
    `BybitRealtimeOrderLookupResult | BybitOrderHistoryOrderFound`."""


@dataclass(frozen=True)
class BybitRealtimeOrderFoundOpen(BybitRealtimeOrderLookupResult):
    """Bybit devolvió, dentro de `/v5/order/realtime` filtrado por
    `orderLinkId`, EXACTAMENTE una orden ABIERTA (`New`/`PartiallyFilled`)
    cuyo `orderLinkId` coincide byte a byte con el `ExecutionOrderId`
    solicitado (correlación verificada por el interpreter, nunca asumida
    por haber sido el filtro de la query).

    Mismo vocabulario de campos que `BybitOrderHistoryOrderFound` (ADR-012
    D16) -- necesario para que un futuro comparador económico (ADR-013
    OQ5) pueda validar `Attempted(X)` contra la observación sin importar
    si la orden se encontró abierta o cerrada -- pero con invariantes
    propias de estado abierto: `filled_quantity` estrictamente menor que
    `quantity` (una orden llena no es "abierta"; sería `Filled`, ADR-012
    D3), `cancel_type` siempre `None` (una orden abierta, por definición,
    nunca fue cancelada), `remote_status` restringido a `{new,
    partially_filled}` -- ver `_VALID_OPEN_STATUSES` para el razonamiento
    de por qué `untriggered`/`triggered` NO son admisibles aquí.

    NO es `OrderObservedOpen` (execution_ledger_event_contracts.py,
    Hito 3.83): no hereda de `ObservedFact`, sin envelope, sin participar
    del Ledger -- resultado tipado de la lectura únicamente."""

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
        if self.filled_quantity >= self.quantity:
            raise ValueError(
                f"filled_quantity must be < quantity for an OPEN order "
                f"(a full fill is 'Filled', not open), "
                f"got: filled_quantity={self.filled_quantity}, quantity={self.quantity}"
            )
        _require_finite_non_negative_decimal(self.filled_value, field="filled_value")

        _require_non_empty_str(self.remote_status, field="remote_status")
        if self.remote_status not in _VALID_OPEN_STATUSES:
            raise ValueError(
                f"remote_status must be one of {sorted(_VALID_OPEN_STATUSES)}, "
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

        if self.reject_reason is not None:
            _require_non_empty_str(self.reject_reason, field="reject_reason")

        # Invariantes cruzadas: "new" nunca tiene ejecución; "partially_filled"
        # siempre tiene ejecución positiva y estrictamente parcial (la cota
        # < quantity ya se exigió arriba, incondicionalmente).
        if self.remote_status == "new" and self.filled_quantity != 0:
            raise ValueError(
                "remote_status == 'new' requires filled_quantity == 0, "
                f"got: filled_quantity={self.filled_quantity}"
            )
        if self.remote_status == "partially_filled" and self.filled_quantity <= 0:
            raise ValueError(
                "remote_status == 'partially_filled' requires filled_quantity > 0, "
                f"got: filled_quantity={self.filled_quantity}"
            )


@dataclass(frozen=True)
class BybitRealtimeOrderNotFound(BybitRealtimeOrderLookupResult):
    """`/v5/order/realtime` no devolvió ninguna fila correlacionada con el
    `ExecutionOrderId` solicitado -- exclusivamente eso.

    NO significa, y NO debe interpretarse como:
      - que X nunca existió ni fue aceptada;
      - que X está rechazada;
      - que X está cerrada (una orden cerrada correlacionada produce
        `BybitOrderHistoryOrderFound`, nunca este resultado -- ver
        `BybitRealtimeOrderLookupResult`);
      - que es seguro reenviar X o una identidad nueva.

    Un MARKET puede llenarse tan rápido que jamás sea visible como
    abierta -- `NOT_FOUND` aquí es compatible con "ya cerró" tanto como
    con "nunca se recibió". La caché de cerradas de este mismo endpoint
    es además volátil entre reinicios de Bybit (ADR-012 F4): un
    `NOT_FOUND` no descarta tampoco que X esté cerrada y simplemente
    fuera de esa caché. Cualquier decisión sobre qué hacer ante este
    resultado (consultar `/v5/order/history`, escalar, esperar) es
    responsabilidad exclusiva de un futuro recovery worker -- fuera de
    alcance del Hito 3.88 (ver ADR-013)."""


__all__ = [
    "BybitRealtimeOrderLookupResult",
    "BybitRealtimeOrderFoundOpen",
    "BybitRealtimeOrderNotFound",
]
