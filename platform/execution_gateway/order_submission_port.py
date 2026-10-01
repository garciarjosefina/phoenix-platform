from typing import Protocol, runtime_checkable

from execution_gateway.contracts import ExecutionRequest
from execution_gateway.order_submission_outcome_contracts import OrderSubmissionOutcome


@runtime_checkable
class OrderSubmissionPort(Protocol):
    """Puerto de submisión de órdenes que PRESERVA la evidencia remota
    (Hito 3.95, ADR-015 D3 / ADR-016 D2).

    A diferencia de `ExecutionGateway.execute(request) -> ExecutionResult`,
    cuyo resultado pierde `server_time_ms` y `ret_code` (ADR-015 F3), este
    puerto devuelve una familia tipada (`OrderSubmissionOutcome`) con
    exactamente los datos remotos que los eventos del Ledger exigen. Es
    exchange-agnóstico: ningún tipo de exchange cruza esta frontera.

    Única operación: `submit`. Recibe el `ExecutionRequest` (sin cuenta ni
    `ExecutionOrderId` adicionales: la identidad Phoenix viaja dentro del
    request y el coordinador la aporta al construir los eventos).

    Contrato de excepciones -- lo implementa cada adapter, este puerto sólo
    lo fija:

    - Un request que el adapter no puede representar, detectado ANTES de
      cualquier red, levanta `ExecutionRequestNotSupportedError`.
    - Los resultados remotos conocidos se DEVUELVEN, nunca se lanzan:
      `SubmissionAccepted`, `SubmissionRejected`,
      `SubmissionIdentityDuplicate`.
    - Un resultado remoto ambiguo (fallo de transporte, respuesta
      malformada, `ret_code` no clasificado, `orderLinkId` no coincidente)
      se DEVUELVE como `SubmissionOutcomeUnknown` -- nunca como excepción ni
      como rechazo.
    - Los errores de programación (`TypeError`, `KeyError`, ...) se propagan
      sin envolver.

    Esta comprobación es estructural (`runtime_checkable` sólo verifica la
    presencia de `submit`); no valida el tipo de retorno.
    """

    def submit(self, request: ExecutionRequest) -> OrderSubmissionOutcome:
        ...


__all__ = ["OrderSubmissionPort"]
