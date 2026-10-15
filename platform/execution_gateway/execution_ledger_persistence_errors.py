class ExecutionLedgerPersistenceError(Exception):
    """Base de los errores de dominio del puerto de persistencia del Execution
    Ledger (Hito 3.98, ADR-011 D2 / ADR-015 D22 / ADR-017 D14).

    Representa semántica del puerto, nunca de un vendor: ninguna subclase
    expone ni hereda de una excepción de un driver. Quien implemente el puerto
    traduce (con `raise ... from error`) y NO deja escapar tipos del driver.
    El mensaje no debe contener credenciales, la URL de conexión ni payloads.
    """

    def __init__(self, *, message: str) -> None:
        if not isinstance(message, str):
            raise TypeError(f"message must be str, got: {type(message).__name__}")
        if not message or message.isspace():
            raise ValueError("message must not be empty or whitespace-only")
        super().__init__(message)
        self.message = message


class LedgerAppendError(ExecutionLedgerPersistenceError):
    """Único error de ESCRITURA del contrato de append (ADR-011 D2): no se
    pudo garantizar la durabilidad. Fail-closed: el caller NO puede asumir ni
    que el evento se persistió ni que no (p. ej. conexión perdida durante el
    commit). Incluye "persistencia no disponible" al escribir. Jamás se
    devuelve un `AppendReceipt` en este caso."""


class LedgerReadError(ExecutionLedgerPersistenceError):
    """El Ledger no pudo leerse (no disponible, conexión perdida). Permite al
    consumidor distinguir "no sé" de "no hay": ADR-015 D13(b) trata un Ledger
    que no responde como cuenta bloqueada, nunca como ledger vacío."""


class LedgerIntegrityError(ExecutionLedgerPersistenceError):
    """Violación de integridad del Ledger, siempre fail-closed y sin
    sobrescritura (ADR-015 D16(b), ADR-017 D7): ya existe un evento con la
    misma clave de contenido pero con contenido estable DISTINTO, o lo
    almacenado está corrupto / no decodifica a un evento válido."""


class LeaseNotAcquiredError(ExecutionLedgerPersistenceError):
    """No se obtuvo la lease exclusiva de la cuenta (otro actor la posee,
    timeout o persistencia no disponible al adquirirla). Sin lease no hay gate
    ni append ni orden (ADR-015 D14, fail-closed)."""


class LeaseLostError(ExecutionLedgerPersistenceError):
    """La lease dejó de ser válida (conexión perdida, handle ya liberado). El
    handle queda inválido para siempre y NUNCA se reconecta en silencio
    (ADR-017 D3.4); cualquier operación posterior falla con este error."""


__all__ = [
    "ExecutionLedgerPersistenceError",
    "LedgerAppendError",
    "LedgerReadError",
    "LedgerIntegrityError",
    "LeaseNotAcquiredError",
    "LeaseLostError",
]
