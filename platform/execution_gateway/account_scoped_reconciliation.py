from execution_gateway.account_scoped_execution_state_contracts import (
    AccountScopedExchangeStateSnapshot,
    AccountScopedExpectedExecutionState,
)
from execution_gateway.cross_account_reconciliation_error import (
    CrossAccountReconciliationError,
)
from execution_gateway.reconciliation_contracts import ReconciliationResult
from execution_gateway.reconciliation_engine import reconcile_execution_state


def reconcile_account_scoped_execution_state(
    *,
    expected: AccountScopedExpectedExecutionState,
    observed: AccountScopedExchangeStateSnapshot,
) -> ReconciliationResult:
    """Capa delgada sobre `reconcile_execution_state` que impide comparar
    cuentas distintas.

    NO reimplementa nada de la reconciliación: no hace matching de
    posiciones ni de órdenes, no filtra por scope, no compara precios, no
    detecta identidades duplicadas y no construye divergencias. Verifica
    la identidad de cuenta y delega; el `ReconciliationResult` que
    devuelve es EXACTAMENTE el objeto que produjo el reconciler aceptado
    (Hito 3.77), sin reconstruirlo ni envolverlo.

    Reconciliation Engine V1 permanece intacto y puro: sigue sin conocer
    la existencia de identidades de cuenta (ADR-005, Decisión 10 -- la
    pertenencia a la misma cuenta era, y sigue siendo *dentro de ese
    componente*, una precondición externa no validada). Lo que cambia es
    que ahora existe una capa exterior capaz de garantizarla.

    Fail-closed ante identidades distintas: comparación exacta de
    `ExecutionAccountId`, sin normalización -- "ACCOUNT-A", "account-a" y
    " ACCOUNT-A " son cuentas distintas.
    """
    if not isinstance(expected, AccountScopedExpectedExecutionState):
        raise TypeError(
            f"expected must be AccountScopedExpectedExecutionState, "
            f"got: {type(expected).__name__}"
        )
    if not isinstance(observed, AccountScopedExchangeStateSnapshot):
        raise TypeError(
            f"observed must be AccountScopedExchangeStateSnapshot, "
            f"got: {type(observed).__name__}"
        )

    if expected.execution_account_id != observed.execution_account_id:
        raise CrossAccountReconciliationError(
            message=(
                f"expected state belongs to execution account "
                f"{expected.execution_account_id.value!r} but observed state belongs to "
                f"{observed.execution_account_id.value!r} -- refusing to reconcile "
                "across execution accounts"
            )
        )

    return reconcile_execution_state(expected=expected.state, observed=observed.state)
