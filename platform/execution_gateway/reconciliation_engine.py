from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot
from execution_gateway.expected_execution_state_contracts import ExpectedExecutionState
from execution_gateway.reconciliation_contracts import (
    Divergence,
    MissingExpectedPosition,
    UnexpectedExchangePosition,
    PositionQuantityMismatch,
    MissingExpectedOpenOrder,
    UnexpectedExchangeOpenOrder,
    UnattributedExchangeOpenOrder,
    OrderSymbolMismatch,
    OrderSideMismatch,
    OrderQuantityMismatch,
    OrderTypeMismatch,
    OrderPriceMismatch,
    ReconciliationResult,
)
from execution_gateway.reconciliation_precondition_error import ReconciliationPreconditionError


def reconcile_execution_state(
    *,
    expected: ExpectedExecutionState,
    observed: ExchangeStateSnapshot,
) -> ReconciliationResult:
    """Función pura: mismos inputs producen siempre el mismo
    ReconciliationResult, con el mismo orden de divergencias. Sin reloj
    local, sin red, sin filesystem, sin variables de entorno, sin estado
    mutable global.

    DETECTION + CLASSIFICATION únicamente -- nunca repara, cancela, crea
    ni modifica nada. `expected` y `observed` deben pertenecer a la misma
    cuenta/configuración -- este componente no lo valida (ADR-004,
    Hito 3.76: ninguno de los dos contratos porta identidad de cuenta
    todavía; resolverlo es una frontera posterior, simétrica y aditiva).
    """
    if not isinstance(expected, ExpectedExecutionState):
        raise TypeError(f"expected must be ExpectedExecutionState, got: {type(expected).__name__}")
    if not isinstance(observed, ExchangeStateSnapshot):
        raise TypeError(f"observed must be ExchangeStateSnapshot, got: {type(observed).__name__}")

    _reject_expected_limit_orders_without_price(expected)
    _reject_duplicate_observed_position_identities(observed)
    _reject_duplicate_observed_order_ids(observed)

    divergences: list[Divergence] = []
    divergences.extend(_reconcile_positions(expected=expected, observed=observed))
    divergences.extend(_reconcile_open_orders(expected=expected, observed=observed))

    return ReconciliationResult(
        divergences=tuple(divergences),
        observation_window=observed.observation_window,
    )


def _reject_expected_limit_orders_without_price(expected: ExpectedExecutionState) -> None:
    # Precondición de entrada, no una divergencia: una orden LIMIT
    # esperada sin precio no es reconciliable en V1 -- fail-closed,
    # nunca se interpreta None como "sin opinión" ni como cero.
    # Recorre expected.open_orders en su orden contractual -- reporta la
    # primera encontrada, determinista.
    for order in expected.open_orders:
        if order.order_type == "limit" and order.price is None:
            raise ReconciliationPreconditionError(
                message=(
                    f"expected LIMIT open order {order.order_id!r} for symbol "
                    f"{order.symbol!r} has no price -- Reconciliation Engine V1 "
                    "cannot reconcile a LIMIT order without an explicit price"
                )
            )


def _reject_duplicate_observed_position_identities(observed: ExchangeStateSnapshot) -> None:
    # Precondición de entrada, no una divergencia: ni PositionsSnapshot ni
    # ExpectedExecutionState exigen unicidad de (symbol, side) en el lado
    # observado. Dos posiciones observadas con la misma identidad son una
    # ambigüedad ESTRUCTURAL del propio snapshot -- no existe una manera
    # determinista de decidir cuál de las dos corresponde realmente a esa
    # identidad, así que V1 falla cerrado en vez de elegir arbitrariamente
    # "la primera" o "la última" (o de sumarlas/netearlas). Se valida
    # sobre TODO observed.positions, incluso para identidades fuera de
    # expected.scope: el scope decide autoridad económica sobre qué se
    # reporta, no si el snapshot observado en sí es válido -- una
    # ambigüedad estructural no debe quedar oculta sólo porque cae fuera
    # de scope. Identidad de string literal y exacta -- sin
    # strip/upper/lower/casefold, igual que en el resto del matching.
    # Recorre observed.positions.positions en su orden contractual --
    # reporta la primera duplicación encontrada, determinista.
    seen: set[tuple[str, str]] = set()
    for position in observed.positions.positions:
        identity = (position.symbol, position.side)
        if identity in seen:
            raise ReconciliationPreconditionError(
                message=(
                    f"observed positions contain duplicate identity (symbol, side) "
                    f"{identity!r} -- Reconciliation Engine V1 cannot determine which "
                    "observed position corresponds to this identity"
                )
            )
        seen.add(identity)


def _reject_duplicate_observed_order_ids(observed: ExchangeStateSnapshot) -> None:
    # Precondición de entrada, no una divergencia: OpenOrdersSnapshot no
    # exige order_id (Phoenix) único entre sus órdenes. Dos órdenes
    # observadas con el mismo order_id son una ambigüedad ESTRUCTURAL --
    # identity-first significa que un order_id Phoenix duplicado ya es
    # ambiguo ANTES de que el scope participe; no se permite que el scope
    # ni ningún atributo económico (symbol/side/quantity) esconda la
    # duplicación. Sólo se valida cuando order_id no es None: dos órdenes
    # huérfanas (order_id is None) NUNCA se consideran duplicadas entre sí
    # por compartir None -- cada una sigue siendo una entidad remota
    # distinta, identificable por su propio exchange_order_id (ver
    # UnattributedExchangeOpenOrder). Identidad de string literal y
    # exacta -- sin normalización. Recorre observed.open_orders.orders en
    # su orden contractual -- reporta la primera duplicación encontrada,
    # determinista.
    seen: set[str] = set()
    for order in observed.open_orders.orders:
        if order.order_id is None:
            continue
        if order.order_id in seen:
            raise ReconciliationPreconditionError(
                message=(
                    f"observed open orders contain duplicate Phoenix order_id "
                    f"{order.order_id!r} -- Reconciliation Engine V1 cannot determine "
                    "which observed order corresponds to this identity"
                )
            )
        seen.add(order.order_id)


def _reconcile_positions(
    *, expected: ExpectedExecutionState, observed: ExchangeStateSnapshot
) -> list[Divergence]:
    divergences: list[Divergence] = []

    # Identidad = (symbol, side). El matching de posiciones ocurre
    # únicamente dentro de expected.scope.symbols (ADR-004, Decisión 2) --
    # una posición observada fuera del scope nunca se declara inesperada,
    # porque Phoenix no tiene autoridad para afirmar nada sobre ella.
    scope_symbols = set(expected.scope.symbols)

    # Seguro construir este dict sin pérdida: _reject_duplicate_observed_
    # position_identities ya rechazó, antes de llegar aquí, cualquier
    # (symbol, side) repetido en observed.positions -- por construcción,
    # a lo sumo una posición observada por identidad.
    observed_by_identity = {
        (position.symbol, position.side): position
        for position in observed.positions.positions
    }
    expected_identities = {(p.symbol, p.side) for p in expected.positions}

    # 1. Recorre expected en su orden contractual -> missing / quantity mismatch.
    for position in expected.positions:
        identity = (position.symbol, position.side)
        observed_position = observed_by_identity.get(identity)
        if observed_position is None:
            divergences.append(
                MissingExpectedPosition(
                    symbol=position.symbol,
                    side=position.side,
                    expected_quantity=position.quantity,
                )
            )
        elif position.quantity != observed_position.quantity:
            divergences.append(
                PositionQuantityMismatch(
                    symbol=position.symbol,
                    side=position.side,
                    expected_quantity=position.quantity,
                    observed_quantity=observed_position.quantity,
                )
            )

    # 2. Recorre observed en su orden contractual -> unexpected dentro de scope.
    for observed_position in observed.positions.positions:
        identity = (observed_position.symbol, observed_position.side)
        if identity in expected_identities:
            continue  # ya procesada en el paso 1 (matched o missing)
        if observed_position.symbol not in scope_symbols:
            continue  # fuera de la autoridad de este scope -- ignorar
        divergences.append(
            UnexpectedExchangePosition(
                symbol=observed_position.symbol,
                side=observed_position.side,
                observed_quantity=observed_position.quantity,
            )
        )

    return divergences


def _reconcile_open_orders(
    *, expected: ExpectedExecutionState, observed: ExchangeStateSnapshot
) -> list[Divergence]:
    divergences: list[Divergence] = []
    scope_symbols = set(expected.scope.symbols)

    # Identidad = order_id Phoenix (ExpectedOpenOrder.order_id <->
    # ExecutionOpenOrder.order_id). exchange_order_id NUNCA participa como
    # fallback -- sólo se usa para UnattributedExchangeOpenOrder, donde no
    # hay order_id Phoenix por definición.
    #
    # Seguro construir este dict sin pérdida: _reject_duplicate_observed_
    # order_ids ya rechazó, antes de llegar aquí, cualquier order_id
    # Phoenix repetido en observed.open_orders -- por construcción, a lo
    # sumo una orden observada por order_id.
    observed_by_order_id = {
        order.order_id: order
        for order in observed.open_orders.orders
        if order.order_id is not None
    }

    matched_order_ids: set[str] = set()

    # 1. IDENTITY-FIRST: recorre expected en su orden contractual. El
    # matching es EXCLUSIVAMENTE por order_id -- el scope NO participa
    # todavía. Una orden matched puede producir múltiples divergencias
    # (una orden puede estar mal en varios campos a la vez); el matching
    # por identidad ya estableció que es la MISMA entidad, así que nunca
    # se reporta también como missing/unexpected.
    for order in expected.open_orders:
        observed_order = observed_by_order_id.get(order.order_id)
        if observed_order is None:
            divergences.append(
                MissingExpectedOpenOrder(
                    order_id=order.order_id,
                    symbol=order.symbol,
                    side=order.side,
                    order_type=order.order_type,
                    quantity=order.quantity,
                )
            )
            continue

        matched_order_ids.add(order.order_id)

        # Orden fijo de comparación: symbol, side, quantity, order_type, price.
        if order.symbol != observed_order.symbol:
            divergences.append(
                OrderSymbolMismatch(
                    order_id=order.order_id,
                    expected_symbol=order.symbol,
                    observed_symbol=observed_order.symbol,
                )
            )
        if order.side != observed_order.side:
            divergences.append(
                OrderSideMismatch(
                    order_id=order.order_id,
                    expected_side=order.side,
                    observed_side=observed_order.side,
                )
            )
        # quantity: siempre expected.quantity vs observed.quantity -- nunca
        # observed.quantity - observed.filled_quantity (remaining). Un
        # partial fill legítimo no es, por sí mismo, una divergencia:
        # observed.quantity es el tamaño original de la orden, invariante
        # ante fills parciales.
        if order.quantity != observed_order.quantity:
            divergences.append(
                OrderQuantityMismatch(
                    order_id=order.order_id,
                    expected_quantity=order.quantity,
                    observed_quantity=observed_order.quantity,
                )
            )
        if order.order_type != observed_order.order_type:
            divergences.append(
                OrderTypeMismatch(
                    order_id=order.order_id,
                    expected_order_type=order.order_type,
                    observed_order_type=observed_order.order_type,
                )
            )
        # price V1: sólo se reconcilia para una orden esperada LIMIT (que
        # ya pasó la precondición de tener price != None). Una orden
        # esperada MARKET nunca produce OrderPriceMismatch -- price no
        # forma parte de la expectativa reconciliable V1 para MARKET,
        # incluso si expected.price viene poblado (semántica heredada,
        # permisiva, de 3.76).
        if order.order_type == "limit":
            if order.price != observed_order.price:
                divergences.append(
                    OrderPriceMismatch(
                        order_id=order.order_id,
                        expected_price=order.price,
                        observed_price=observed_order.price,
                    )
                )

    # 2. SCOPE-SECOND: recorre observed en su orden contractual para lo
    # que NO fue matched por identidad Phoenix.
    for observed_order in observed.open_orders.orders:
        if observed_order.order_id is not None and observed_order.order_id in matched_order_ids:
            continue  # ya procesada en el paso 1

        if observed_order.order_id is None:
            # Orden huérfana: sin identidad Phoenix atribuible.
            if observed_order.symbol not in scope_symbols:
                continue  # fuera de la autoridad de este scope -- ignorar
            divergences.append(
                UnattributedExchangeOpenOrder(
                    exchange_order_id=observed_order.exchange_order_id,
                    symbol=observed_order.symbol,
                    side=observed_order.side,
                    order_type=observed_order.order_type,
                    quantity=observed_order.quantity,
                )
            )
            continue

        # order_id Phoenix presente, pero no matcheó ningún expected.
        # Ahora sí entra en juego el scope.
        if observed_order.symbol not in scope_symbols:
            continue  # fuera de la autoridad de este scope -- ignorar
        divergences.append(
            UnexpectedExchangeOpenOrder(
                order_id=observed_order.order_id,
                symbol=observed_order.symbol,
                side=observed_order.side,
                order_type=observed_order.order_type,
                quantity=observed_order.quantity,
            )
        )

    return divergences
