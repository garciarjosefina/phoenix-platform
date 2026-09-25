from execution_gateway.economic_comparison_contracts import (
    EconomicComparisonResult,
    EconomicOrderTypeMismatch,
    EconomicPriceMismatch,
    EconomicQuantityMismatch,
    EconomicReduceOnlyMismatch,
    EconomicSideMismatch,
    EconomicSymbolMismatch,
)
from execution_gateway.economic_comparison_precondition_error import (
    EconomicComparisonPreconditionError,
)
from execution_gateway.execution_ledger_event_contracts import OrderSubmissionAttempted
from execution_gateway.observed_order_economics_contracts import ObservedOrderEconomics

# ADR-014 D7: `OrderSubmissionAttempted` (Hito 3.83, contrato aceptado y
# congelado) no porta `reduce_only` -- el adapter actual
# (`bybit_gateway._to_bybit_request`) lo fija incondicionalmente a
# `False`. Mientras esa constante siga vigente, el lado "attempted" de
# esta dimensión usa esa misma semántica constante. NO se modifica
# OrderSubmissionAttempted aquí; el tripwire causal que protege esta
# suposición es responsabilidad explícita del Hito 3.92 (ADR-014,
# Resolución del STOP), no de este comparador.
_ATTEMPTED_REDUCE_ONLY = False


def compare_attempted_order_to_observed_economics(
    *, attempted: OrderSubmissionAttempted, observed: ObservedOrderEconomics
) -> EconomicComparisonResult:
    """Economic Comparator -- Hito 3.91, ADR-014.

    Responde exclusivamente: "¿la evidencia remota observada para `X`
    describe la misma orden económica que `Attempted(X)`?" (ADR-014 D1).
    NUNCA decide reenviar, recuperar, aceptar, rechazar, cerrar la orden,
    ni si una divergencia debe repararse -- sólo informa.

    Función pura y determinista (ADR-014 D14): sin reloj, sin
    aleatoriedad, sin red, sin storage, sin variables de entorno, sin
    estado mutable global. Mismos inputs producen siempre el mismo
    `EconomicComparisonResult`, con la misma tupla en el mismo orden.

    Verificación defensiva de identidad (ADR-014 D9): si
    `attempted.execution_order_id` y `observed.execution_order_id` no
    coinciden, levanta `EconomicComparisonPreconditionError` -- NUNCA
    devuelve una divergencia ni un `MISMATCH`. Una identidad cruzada es
    un defecto de programación del caller, no un hecho económico sobre
    el mundo (ADR-014 D11/D19).

    Compara exactamente seis dimensiones económicas, en este orden fijo
    (ADR-014 D2/D12/D18): `symbol`, `side`, `order_type`, `quantity`,
    `price`, `reduce_only`. Nunca compara `filled_quantity`,
    `filled_value`, `average_price`, `remote_status`, `exchange_order_id`,
    timestamps, `cancel_type` ni `reject_reason` -- esos campos no
    existen siquiera en `ObservedOrderEconomics` (ADR-014 D8), así que su
    exclusión es estructural, no una omisión de esta función.

    Igualdad `Decimal` exacta por valor (ADR-014 D5): `Decimal("1") ==
    Decimal("1.000")` es `True` y se trata como MATCH -- nunca se
    convierte a `float`, nunca se introduce epsilon ni `quantize`.
    `price` compara el valor ORIGINAL en ambos lados (nunca
    `average_price`, ADR-014 D4): para `market`, ambos lados son `None`
    por invariante de los contratos de origen (ADR-014 F6), y la
    comparación es trivialmente un MATCH."""
    if not isinstance(attempted, OrderSubmissionAttempted):
        raise TypeError(
            f"attempted must be OrderSubmissionAttempted, got: {type(attempted).__name__}"
        )
    if not isinstance(observed, ObservedOrderEconomics):
        raise TypeError(
            f"observed must be ObservedOrderEconomics, got: {type(observed).__name__}"
        )

    if attempted.execution_order_id != observed.execution_order_id:
        raise EconomicComparisonPreconditionError(
            message=(
                "attempted.execution_order_id and observed.execution_order_id "
                "must be the same identity -- comparing Attempted(X) against an "
                "observation of a different identity is a caller defect, never "
                "an economic mismatch"
            )
        )

    divergences: list = []

    if attempted.symbol != observed.symbol:
        divergences.append(
            EconomicSymbolMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_symbol=attempted.symbol,
                observed_symbol=observed.symbol,
            )
        )

    if attempted.side != observed.side:
        divergences.append(
            EconomicSideMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_side=attempted.side,
                observed_side=observed.side,
            )
        )

    if attempted.order_type != observed.order_type:
        divergences.append(
            EconomicOrderTypeMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_order_type=attempted.order_type,
                observed_order_type=observed.order_type,
            )
        )

    if attempted.quantity != observed.quantity:
        divergences.append(
            EconomicQuantityMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_quantity=attempted.quantity,
                observed_quantity=observed.quantity,
            )
        )

    if attempted.price != observed.price:
        divergences.append(
            EconomicPriceMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_price=attempted.price,
                observed_price=observed.price,
            )
        )

    if _ATTEMPTED_REDUCE_ONLY != observed.reduce_only:
        divergences.append(
            EconomicReduceOnlyMismatch(
                execution_order_id=attempted.execution_order_id,
                attempted_reduce_only=_ATTEMPTED_REDUCE_ONLY,
                observed_reduce_only=observed.reduce_only,
            )
        )

    return EconomicComparisonResult(divergences=tuple(divergences))


__all__ = ["compare_attempted_order_to_observed_economics"]
