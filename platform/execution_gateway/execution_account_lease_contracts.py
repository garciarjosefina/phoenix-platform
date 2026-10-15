from typing import Protocol, runtime_checkable

from execution_gateway.execution_identity_contracts import ExecutionAccountId
from execution_gateway.execution_ledger_persistence_contracts import (
    ExecutionLedgerReader,
    ExecutionLedgerWriter,
)


@runtime_checkable
class AccountLeaseHandle(Protocol):
    """Lease EXCLUSIVA vigente sobre una `ExecutionAccountId` (ADR-015 D14,
    ADR-017 D3). Expone sólo semántica estable, sin ningún detalle del medio
    de persistencia:

    - `execution_account_id`: la cuenta que posee.
    - `writer` / `reader`: el Writer y el Reader vinculados a ESTA lease. Toda
      operación sobre la cuenta mientras la lease exista pasa por ellos, de
      modo que Writer, Reader y lease comparten una única sesión conceptual
      (ADR-017 D3.2: sin eso el append se auto-bloquearía).
    - `release()`: libera la lease; tras liberar, el handle queda inválido.

    Nunca reconecta en silencio. Si la lease se pierde (conexión caída,
    handle ya liberado), cualquier operación posterior levanta
    `LeaseLostError` y el handle no vuelve a ser válido (ADR-017 D3.4).
    """

    @property
    def execution_account_id(self) -> ExecutionAccountId:
        ...

    @property
    def writer(self) -> ExecutionLedgerWriter:
        ...

    @property
    def reader(self) -> ExecutionLedgerReader:
        ...

    def release(self) -> None:
        ...


@runtime_checkable
class AccountExecutionLease(Protocol):
    """Puerto de adquisición de la lease de cuenta (ADR-015 D14/D22).

    `acquire` devuelve el handle de una lease EXCLUSIVA o levanta
    `LeaseNotAcquiredError` (otro actor la posee, timeout o persistencia no
    disponible): sin lease no hay orden (fail-closed). Deliberadamente SIN
    parámetro de timeout: la política de tiempos queda para la implementación
    (ADR-015 OQ3), no se inventa aquí.
    """

    def acquire(self, *, execution_account_id: ExecutionAccountId) -> AccountLeaseHandle:
        ...


__all__ = ["AccountLeaseHandle", "AccountExecutionLease"]
