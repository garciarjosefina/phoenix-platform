from dataclasses import dataclass

# Conjunto cerrado de categorías de indeterminación -- ADR-016 D2: idéntico al
# `_VALID_OUTCOME_UNKNOWN_REASONS` del Execution Ledger (Hito 3.83), duplicado
# aquí deliberadamente para que este módulo NO importe el módulo del Ledger
# (mismo criterio que los helpers duplicados de 3.94). La igualdad exacta
# entre ambos conjuntos se fija desde los tests, nunca por acoplamiento de
# producción.
_VALID_UNKNOWN_REASONS = {
    "transport_failure",
    "malformed_response",
    "ambiguous_business_response",
    "identity_mismatch",
}

# ADR-013 D3 / Resolución del STOP: `110072` ("identidad duplicada") no es un
# rechazo de la orden sino evidencia de existencia de la identidad.
_DUPLICATE_IDENTITY_RET_CODE = 110072


def _require_non_empty_str(value, *, field: str) -> None:
    # Identidad de string literal y exacta -- sin strip/upper/lower/casefold,
    # mismo patrón ya usado en todo el bounded context (ADR-005, Decisión 3).
    if not isinstance(value, str):
        raise TypeError(f"{field} must be str, got: {type(value).__name__}")
    if not value or value.isspace():
        raise ValueError(f"{field} must not be empty or whitespace-only")


def _require_non_negative_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{field} must be >= 0, got: {value}")


def _require_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")


class OrderSubmissionOutcome:
    """Marcador no instanciable, base de todo resultado de una submisión de
    orden (Hito 3.95, ADR-015 D3 / ADR-016 D2).

    Existen exactamente cuatro subtipos concretos, nunca un quinto estado ni
    un campo de status libre: `SubmissionAccepted`, `SubmissionRejected`,
    `SubmissionIdentityDuplicate` y `SubmissionOutcomeUnknown`. La
    clasificación es el propio tipo Python (mismo patrón que `Divergence` y
    que la familia de lookup de 3.86/3.88), nunca un string en un campo.

    Cada subtipo es la evidencia remota YA CLASIFICADA de una única llamada de
    creación de orden, con exactamente los campos que el coordinador necesita
    para construir el evento del Ledger correspondiente. Ninguno porta
    `execution_order_id`: la identidad Phoenix de la orden la posee el
    coordinador, que la aporta al construir el evento. Por eso, para cada par,
    `campos(evento) == campos(outcome) | {"execution_order_id"}`.

    No es un evento del Ledger ni participa de sus marcadores de autoridad
    (`LocalFact`/`RemoteFact`/`ObservedFact` pertenecen al modelo de eventos).
    Este módulo no importa el Ledger, ningún adapter ni ningún tipo específico
    de exchange.
    """


@dataclass(frozen=True)
class SubmissionAccepted(OrderSubmissionOutcome):
    """El exchange confirmó explícitamente la creación de la orden.

    `exchange_order_id` es la identidad remota, preservada literalmente.
    `server_time_ms` es el tiempo de generación de la respuesta del exchange
    (metadato de la respuesta, nunca tiempo de creación de la orden ni de
    fill). Corresponde 1:1, salvo `execution_order_id`, a
    `OrderAcceptedByExchange`.
    """

    exchange_order_id: str
    server_time_ms: int

    def __post_init__(self) -> None:
        _require_non_empty_str(self.exchange_order_id, field="exchange_order_id")
        _require_non_negative_int(self.server_time_ms, field="server_time_ms")


@dataclass(frozen=True)
class SubmissionRejected(OrderSubmissionOutcome):
    """El exchange rechazó explícitamente la orden (rechazo de negocio).

    `ret_code`/`ret_msg` se preservan verbatim, sin normalizar. NUNCA
    representa `110072`: un duplicado de identidad es evidencia de existencia
    de la identidad, no un rechazo terminal de la orden original
    (`SubmissionIdentityDuplicate`). Corresponde 1:1, salvo
    `execution_order_id`, a `OrderRejectedByExchange`.
    """

    ret_code: int
    ret_msg: str
    server_time_ms: int

    def __post_init__(self) -> None:
        _require_int(self.ret_code, field="ret_code")
        if self.ret_code == _DUPLICATE_IDENTITY_RET_CODE:
            raise ValueError(
                "ret_code must not be 110072 (ADR-013 D3): a duplicate-identity "
                "response is never a rejection of the order -- use "
                "SubmissionIdentityDuplicate"
            )
        _require_non_empty_str(self.ret_msg, field="ret_msg")
        _require_non_negative_int(self.server_time_ms, field="server_time_ms")


@dataclass(frozen=True)
class SubmissionIdentityDuplicate(OrderSubmissionOutcome):
    """El exchange respondió `110072` ("OrderLinkedID is duplicate").

    Evidencia remota de que la identidad ya existe o existió -- NO un rechazo
    ni una aceptación de la orden (ADR-013 D1-D4). Deliberadamente NO hereda
    de `SubmissionRejected`. `ret_code` es invariante: exactamente `110072`.
    Corresponde 1:1, salvo `execution_order_id`, a
    `OrderIdentityReportedDuplicateByExchange`.
    """

    ret_code: int
    ret_msg: str
    server_time_ms: int

    def __post_init__(self) -> None:
        _require_int(self.ret_code, field="ret_code")
        if self.ret_code != _DUPLICATE_IDENTITY_RET_CODE:
            raise ValueError(
                f"ret_code must be exactly 110072 in V1 (ADR-013), got: {self.ret_code}"
            )
        _require_non_empty_str(self.ret_msg, field="ret_msg")
        _require_non_negative_int(self.server_time_ms, field="server_time_ms")


@dataclass(frozen=True)
class SubmissionOutcomeUnknown(OrderSubmissionOutcome):
    """Phoenix no puede afirmar aceptación ni rechazo: la llamada terminó de
    forma ambigua (transporte, respuesta malformada, `ret_code` no
    clasificado o `orderLinkId` no coincidente).

    `reason` es una categoría descriptiva del conjunto cerrado de ADR-010 D3 /
    Hito 3.83, nunca una decisión (`should_retry` y similares están
    prohibidos). Sin tiempo remoto: no hay una respuesta interpretable de la
    que tomarlo. Corresponde 1:1, salvo `execution_order_id`, a
    `OrderSubmissionOutcomeUnknown`.
    """

    reason: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.reason, field="reason")
        if self.reason not in _VALID_UNKNOWN_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(_VALID_UNKNOWN_REASONS)}, "
                f"got: {self.reason!r}"
            )


__all__ = [
    "OrderSubmissionOutcome",
    "SubmissionAccepted",
    "SubmissionRejected",
    "SubmissionIdentityDuplicate",
    "SubmissionOutcomeUnknown",
]
