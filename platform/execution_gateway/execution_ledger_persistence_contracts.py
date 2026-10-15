from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionLedgerEvent,
    ExecutionLedgerEventId,
    ExecutionLedgerEventPayload,
)


def _require_positive_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")
    if value < 1:
        raise ValueError(f"{field} must be >= 1, got: {value}")


def _require_non_negative_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{field} must be >= 0, got: {value}")


@dataclass(frozen=True)
class AppendReceipt:
    """Confirmación de un append DURABLE (ADR-011 D2). Se construye
    únicamente después de que el commit durable retornó; nunca antes ni en un
    fallo.

    `event_id`: identidad del registro, GENERADA por el Writer (ADR-011 D3).
    `execution_account_id`: cuenta del ledger en que se escribió.
    `sequence`: orden de commit DENTRO de esa cuenta (ADR-011 D4, ADR-015
    D15), >= 1, asignada por el Writer dentro de la transacción del append;
    no garantiza causalidad remota ni orden entre cuentas distintas.
    `committed_at_ms`: tiempo de ALMACENAMIENTO asignado por el Writer (reloj
    del servidor de persistencia, ADR-017 D6), distinto de `occurred_at_ms`
    (tiempo de dominio, ADR-010 D8): nunca se confunden ni se sustituyen.

    Deliberadamente SIN el payload, SIN `occurred_at_ms` y SIN ningún
    identificador específico de una base de datos.
    """

    event_id: ExecutionLedgerEventId
    execution_account_id: ExecutionAccountId
    sequence: int
    committed_at_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, ExecutionLedgerEventId):
            raise TypeError(
                f"event_id must be ExecutionLedgerEventId, got: {type(self.event_id).__name__}"
            )
        if not isinstance(self.execution_account_id, ExecutionAccountId):
            raise TypeError(
                f"execution_account_id must be ExecutionAccountId, "
                f"got: {type(self.execution_account_id).__name__}"
            )
        _require_positive_int(self.sequence, field="sequence")
        _require_non_negative_int(self.committed_at_ms, field="committed_at_ms")


@dataclass(frozen=True)
class StoredExecutionLedgerEvent:
    """Evento tal como lo devuelve el Reader: el `ExecutionLedgerEvent` del
    dominio (sin modificar) más los dos metadatos de almacenamiento que el
    envelope no porta (ADR-011 D13/D14, ADR-017 D6): `sequence` y
    `committed_at_ms`. Mismas reglas que en `AppendReceipt`.

    Es un valor de lectura: no existe ninguna operación para mutarlo ni para
    reescribirlo en el Ledger.
    """

    event: ExecutionLedgerEvent
    sequence: int
    committed_at_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.event, ExecutionLedgerEvent):
            raise TypeError(
                f"event must be ExecutionLedgerEvent, got: {type(self.event).__name__}"
            )
        _require_positive_int(self.sequence, field="sequence")
        _require_non_negative_int(self.committed_at_ms, field="committed_at_ms")


@runtime_checkable
class ExecutionLedgerWriter(Protocol):
    """Puerto de ESCRITURA del Execution Ledger. Sólo agrega (append-only):
    no existe ni existirá update/delete/replace/upsert (ADR-011 D13).

    Contrato (ADR-011 D2, ADR-015 D4/D16, ADR-017 D3/D6):
    - Recibe cuenta, `occurred_at_ms` (tiempo de dominio, provisto por el
      caller) y el PAYLOAD; NO recibe un `ExecutionLedgerEvent` ni un
      `event_id`: el Writer genera la identidad del evento (UUID4) y asigna
      `sequence` y `committed_at_ms`.
    - Devuelve el `AppendReceipt` ÚNICAMENTE después de que el commit durable
      retornó. Sin commit confirmado no hay receipt: levanta `LedgerAppendError`.
    - Ante colisión de clave de contenido: mismo contenido estable ⇒ devuelve
      el receipt del registro ya existente (éxito idempotente); contenido
      distinto ⇒ `LedgerIntegrityError`, sin sobrescritura (ADR-015 D16).
    - Sin `append_many`, sin batch, sin async.
    - Una implementación vinculada a una lease de cuenta rechaza otra cuenta.
    """

    def append(
        self,
        *,
        execution_account_id: ExecutionAccountId,
        occurred_at_ms: int,
        payload: ExecutionLedgerEventPayload,
    ) -> AppendReceipt:
        ...


@runtime_checkable
class ExecutionLedgerReader(Protocol):
    """Puerto de LECTURA NEUTRAL del Execution Ledger (ADR-017 D13). Expone
    hechos almacenados, nunca política: no define qué evento "resuelve" una
    orden, ni "bloqueada", ni "pendiente" — eso pertenece al Gate (ADR-015
    D13, OQ1). Todas las lecturas devuelven eventos en orden de `sequence`
    ascendente, que es el único orden de replay (ADR-011 D13).

    Un fallo de lectura levanta `LedgerReadError` (nunca una lista vacía:
    "no sé" no es "no hay"); un evento almacenado corrupto, `LedgerIntegrityError`.
    El tipo de evento se identifica por la CLASE del payload, no por un string.
    """

    def read_account_events(
        self, *, execution_account_id: ExecutionAccountId
    ) -> tuple[StoredExecutionLedgerEvent, ...]:
        ...

    def read_order_events(
        self,
        *,
        execution_account_id: ExecutionAccountId,
        execution_order_id: ExecutionOrderId,
    ) -> tuple[StoredExecutionLedgerEvent, ...]:
        ...

    def read_last_order_event(
        self,
        *,
        execution_account_id: ExecutionAccountId,
        execution_order_id: ExecutionOrderId,
        payload_type: type[ExecutionLedgerEventPayload],
    ) -> StoredExecutionLedgerEvent | None:
        ...

    def read_order_ids_with_event_type(
        self,
        *,
        execution_account_id: ExecutionAccountId,
        payload_type: type[ExecutionLedgerEventPayload],
    ) -> tuple[ExecutionOrderId, ...]:
        ...


__all__ = [
    "AppendReceipt",
    "StoredExecutionLedgerEvent",
    "ExecutionLedgerWriter",
    "ExecutionLedgerReader",
]
