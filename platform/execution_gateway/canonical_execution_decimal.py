import math
from decimal import Decimal

from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError

_NON_FINITE_MESSAGE = "Execution economic value must be finite"


def canonical_execution_decimal(value: float) -> Decimal:
    """Autoridad canónica ÚNICA (ADR-014, Resolución del STOP de Hito 3.90,
    Decisión 2; Hito 3.92) para la conversión `float -> Decimal` de un
    valor económico de ejecución (`quantity`/`price`).

    Semántica exacta y congelada: `Decimal(str(value))` -- ninguna otra.
    Prohibido explícitamente por ADR-014: `Decimal(value)` directamente
    desde `float` (introduce el error de representación binaria que
    `str()` evita -- `str(float)` produce siempre la representación
    decimal más corta que reconstruye exactamente ese `float`),
    `Decimal.from_float(value)` (mismo problema, API distinta), y
    cualquier `round()`/`quantize()` antes o después de la conversión
    (colapsarían valores económicamente distintos en uno solo -- la
    vulnerabilidad exacta de la que depende el Economic Comparator
    aceptado en Hito 3.91 para no producir falsos `MATCH`).

    Frontera de input: exactamente la que `ExecutionRequest.quantity`/
    `price` ya aceptan hoy (`float`) -- esta función no amplía ni
    angosta esa frontera con un `isinstance` nuevo, para no introducir
    una segunda política de validación en conflicto con el Port. Un
    valor no finito (`NaN`, `+Infinity`, `-Infinity`) se rechaza con
    `ExecutionRequestNotSupportedError`, exactamente igual que la
    implementación privada que reemplaza dentro del único adapter de
    ejecución existente (hito anterior a 3.92).

    Pura y determinista: sin reloj, sin entorno, sin red, sin storage,
    sin estado mutable compartido -- el mismo `float` produce siempre
    el mismo `Decimal`.

    Única autoridad reutilizable por (1) el mapping económico del
    adapter de ejecución hacia el cable y (2) la futura construcción
    durable de `OrderSubmissionAttempted` -- Hito 3.92 NO construye ese
    wrapper, sólo deja lista la autoridad que reutilizará sin
    reimplementarla."""
    if not math.isfinite(value):
        raise ExecutionRequestNotSupportedError(message=_NON_FINITE_MESSAGE)
    return Decimal(str(value))
