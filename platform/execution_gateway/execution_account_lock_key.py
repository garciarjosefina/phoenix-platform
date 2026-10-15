import hashlib

from execution_gateway.execution_identity_contracts import ExecutionAccountId

# ADR-017 D5: dominio + versión en el prefijo. Cambiar el algoritmo exige un
# prefijo nuevo (`v2`) y detener antes todos los procesos de la cuenta: dos
# algoritmos simultáneos no se excluirían.
_LOCK_KEY_NAMESPACE = b"phoenix:execution-account-lease:v1:"
_LOCK_KEY_BYTES = 8


def account_lock_key(execution_account_id: ExecutionAccountId) -> int:
    """Clave del advisory lock de una cuenta (ADR-017 D5): los primeros 8
    bytes de SHA-256(`phoenix:execution-account-lease:v1:` + el `value` de la
    cuenta en UTF-8), leídos como entero big-endian CON signo — el rango de un
    `bigint` de 64 bits.

    Pura y determinista: sin `hash()` de Python (aleatorizado por proceso),
    sin azar, sin reloj, sin entorno, sin secretos; el mismo id da la misma
    clave en cualquier proceso y reinicio. Una colisión accidental entre dos
    cuentas (≈ n²/2⁶⁵) sólo provoca serialización espuria entre ellas: es un
    riesgo de disponibilidad, no de integridad.
    """
    if not isinstance(execution_account_id, ExecutionAccountId):
        raise TypeError(
            f"execution_account_id must be ExecutionAccountId, "
            f"got: {type(execution_account_id).__name__}"
        )
    digest = hashlib.sha256(_LOCK_KEY_NAMESPACE + execution_account_id.value.encode("utf-8")).digest()
    return int.from_bytes(digest[:_LOCK_KEY_BYTES], "big", signed=True)


__all__ = ["account_lock_key"]
