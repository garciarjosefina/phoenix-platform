from dataclasses import dataclass

from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot
from execution_gateway.execution_identity_contracts import ExecutionAccountId
from execution_gateway.expected_execution_state_contracts import ExpectedExecutionState


@dataclass(frozen=True)
class AccountScopedExpectedExecutionState:
    """Ata un `ExpectedExecutionState` a la cuenta de ejecución sobre la
    que Phoenix lo afirma.

    ENVUELVE, no reescribe: `ExpectedExecutionState` (Hito 3.76, aceptado)
    no se modificó para insertarle `account_id`, y este wrapper NO copia
    ni reconstruye `scope`/`positions`/`open_orders` -- transporta el
    objeto real, preservado por identidad. Un consumidor que quiera el
    estado lo obtiene tal cual fue construido.

    Lleva únicamente `ExecutionAccountId` (identidad interna de Phoenix),
    no `ExchangeAccountIdentity`. La garantía que este wrapper existe
    para dar -- no comparar la expectativa de una cuenta contra la
    observación de otra -- se obtiene enteramente con la identidad
    interna. Verificar que esa identidad interna corresponde realmente a
    una cuenta remota concreta es *binding verification*, responsabilidad
    del futuro Account Registry, que no existe (ADR-008).

    Sigue siendo account-level: no porta `bot_id`. La atribución por bot
    vivirá en el futuro Ledger como dimensión separada.
    """

    execution_account_id: ExecutionAccountId
    state: ExpectedExecutionState

    def __post_init__(self) -> None:
        if not isinstance(self.execution_account_id, ExecutionAccountId):
            raise TypeError(
                f"execution_account_id must be ExecutionAccountId, "
                f"got: {type(self.execution_account_id).__name__}"
            )
        if not isinstance(self.state, ExpectedExecutionState):
            raise TypeError(
                f"state must be ExpectedExecutionState, got: {type(self.state).__name__}"
            )


@dataclass(frozen=True)
class AccountScopedExchangeStateSnapshot:
    """Contraparte simétrica del wrapper esperado, para el lado observado.

    Misma regla: `ExchangeStateSnapshot` (Hito 3.74, aceptado) no se
    modificó, no se copian sus sub-snapshots y no se reconstruye su
    `ObservationWindow` -- el snapshot viaja preservado por identidad, y
    por tanto su ventana de observación también lo hace transitivamente
    (garantía verificada en 3.77 y protegida por tests).

    La simetría es deliberada: si sólo un lado portara identidad de
    cuenta, la comparación entre ambos no podría verificarse
    estructuralmente.
    """

    execution_account_id: ExecutionAccountId
    state: ExchangeStateSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.execution_account_id, ExecutionAccountId):
            raise TypeError(
                f"execution_account_id must be ExecutionAccountId, "
                f"got: {type(self.execution_account_id).__name__}"
            )
        if not isinstance(self.state, ExchangeStateSnapshot):
            raise TypeError(
                f"state must be ExchangeStateSnapshot, got: {type(self.state).__name__}"
            )
