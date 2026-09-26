from execution_gateway.observed_order_economics_contracts import ObservedOrderEconomics
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderFoundOpen


def project_open_order_to_observed_economics(
    *, open_order: BybitRealtimeOrderFoundOpen
) -> ObservedOrderEconomics:
    """Proyección MECÁNICA (Hito 3.91, ADR-014 Contrato Conceptual, punto
    B): copia los siete campos homónimos de una orden abierta encontrada
    por `orderLinkId` (Hito 3.88) a `ObservedOrderEconomics` --
    `execution_order_id`, `symbol`, `side`, `order_type`, `quantity`,
    `price` y `reduce_only`, este último SÍ copiado literalmente: es una
    de las siete dimensiones (ADR-014 D8/D2), nunca una de las ignoradas.

    Sin normalización adicional (symbol/side/order_type ya llegan
    normalizados desde el interpreter de 3.88, ADR-014 D6), sin I/O, sin
    reloj, sin storage, sin lógica condicional más allá de la que el
    propio contrato de origen ya garantiza. Deliberadamente ignora el
    resto de los campos de `BybitRealtimeOrderFoundOpen` -- metadata y
    evolución, nunca intención económica (ADR-014 D8): `exchange_order_id`,
    `filled_quantity`, `filled_value`, `average_price`, `remote_status`,
    `reject_reason`, `server_time_ms`, `remote_created_time_ms` y
    `remote_updated_time_ms`."""
    if not isinstance(open_order, BybitRealtimeOrderFoundOpen):
        raise TypeError(
            f"open_order must be BybitRealtimeOrderFoundOpen, "
            f"got: {type(open_order).__name__}"
        )
    return ObservedOrderEconomics(
        execution_order_id=open_order.execution_order_id,
        symbol=open_order.symbol,
        side=open_order.side,
        order_type=open_order.order_type,
        quantity=open_order.quantity,
        price=open_order.price,
        reduce_only=open_order.reduce_only,
    )


def project_closed_order_to_observed_economics(
    *, closed_order: BybitOrderHistoryOrderFound
) -> ObservedOrderEconomics:
    """Proyección MECÁNICA (Hito 3.91, ADR-014 Contrato Conceptual, punto
    C): copia los siete campos homónimos de una orden cerrada encontrada
    por `orderLinkId` (Hito 3.86) a `ObservedOrderEconomics`.

    Sin branching por `remote_status` (`filled`/`cancelled`/`rejected`):
    el estado terminal no altera la economía original (ADR-014 D3/D4/D8).
    Ignora deliberadamente `exchange_order_id`, `filled_quantity`,
    `filled_value`, `average_price`, `remote_status`, `cancel_type`,
    `reject_reason` y ambos timestamps remotos -- ninguno participa de
    la intención económica original."""
    if not isinstance(closed_order, BybitOrderHistoryOrderFound):
        raise TypeError(
            f"closed_order must be BybitOrderHistoryOrderFound, "
            f"got: {type(closed_order).__name__}"
        )
    return ObservedOrderEconomics(
        execution_order_id=closed_order.execution_order_id,
        symbol=closed_order.symbol,
        side=closed_order.side,
        order_type=closed_order.order_type,
        quantity=closed_order.quantity,
        price=closed_order.price,
        reduce_only=closed_order.reduce_only,
    )


__all__ = [
    "project_open_order_to_observed_economics",
    "project_closed_order_to_observed_economics",
]
