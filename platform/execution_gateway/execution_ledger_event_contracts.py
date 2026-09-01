from dataclasses import dataclass
from decimal import Decimal

from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId

_VALID_SIDES = {"buy", "sell"}
_VALID_ORDER_TYPES = {"market", "limit"}
_VALID_OPEN_ORDER_STATUSES = {"new", "partially_filled", "untriggered", "triggered"}
_VALID_OUTCOME_UNKNOWN_REASONS = {
    "transport_failure",
    "malformed_response",
    "ambiguous_business_response",
    "identity_mismatch",
}


def _require_non_empty_str(value, *, field: str) -> None:
    # Identidad de string literal y exacta -- sin strip/upper/lower/casefold,
    # mismo patrón ya usado en todo el bounded context (ADR-005, Decisión 3;
    # ADR-009).
    if not isinstance(value, str):
        raise TypeError(f"{field} must be str, got: {type(value).__name__}")
    if not value or value.isspace():
        raise ValueError(f"{field} must not be empty or whitespace-only")


def _require_side(value, *, field: str) -> None:
    _require_non_empty_str(value, field=field)
    if value not in _VALID_SIDES:
        raise ValueError(f"{field} must be 'buy' or 'sell', got: {value!r}")


def _require_order_type(value, *, field: str) -> None:
    _require_non_empty_str(value, field=field)
    if value not in _VALID_ORDER_TYPES:
        raise ValueError(f"{field} must be 'market' or 'limit', got: {value!r}")


def _require_finite_positive_decimal(value, *, field: str) -> None:
    if not isinstance(value, Decimal):
        raise TypeError(f"{field} must be Decimal, got: {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"{field} must be finite")
    if value <= 0:
        raise ValueError(f"{field} must be > 0, got: {value}")


def _require_non_negative_int(value, *, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{field} must be int, got: {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{field} must be >= 0, got: {value}")


# ---------------------------------------------------------------------------
# Identidades propias del Execution Ledger (ADR-010)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionBotId:
    """Identidad OPCIONAL de bot dentro del bounded context de ejecución
    (ADR-010, resolución de OQ1 — 2026-08-27).

    RECIBIDA, nunca autogenerada: mismo patrón que `ExecutionAccountId`
    (ADR-009). No hay formato textual oficial congelado -- no existe
    todavía la autoridad que lo acuñaría, exactamente la misma razón por
    la que `ExecutionAccountId` tampoco tiene uno.

    NO se importa `phoenix_core.ids.bot_id()`: violaría el mismo
    aislamiento de bounded context ya verificado por AST en el Hito 3.81
    (`phoenix_core` está congelado en v0.1.0 y `execution_gateway` no lo
    importa en ningún archivo productivo).

    Su ausencia en un evento NO significa "bot desconocido" -- significa
    "este evento no declara ownership por bot" (p. ej. un futuro flujo
    disparado por Dashboard, no por un bot). Nunca se infiere ni se
    genera automáticamente cuando falta.
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.value, field="value")


@dataclass(frozen=True)
class ExecutionLedgerEventId:
    """Identidad del propio hecho registrado en el Execution Ledger (ADR-010,
    Decisión 6) -- distinta de `ExecutionOrderId` (identifica una orden,
    no un evento) y de `ExecutionAccountId`.

    RECIBIDA, nunca autogenerada en `__post_init__`. Deliberadamente SIN
    generador y SIN formato textual congelado: a diferencia de
    `ExecutionOrderId`, este identificador nunca cruza la frontera de
    Bybit, así que no existe ninguna restricción externa que derivar
    (ADR-010, Decisión 6) -- mismo tratamiento que `ExecutionAccountId`
    (ADR-009, OQ1), no un generador con formato distinto como
    `ExecutionOrderId`.

    NO es una clave de idempotencia (ADR-010, Decisión 7): identifica el
    *registro* de un hecho, no el hecho del mundo real que describe.
    """

    value: str

    def __post_init__(self) -> None:
        _require_non_empty_str(self.value, field="value")


# ---------------------------------------------------------------------------
# Payloads -- clase marcadora + tres marcadores de autoridad + cinco tipos
# concretos (ADR-010, Decisiones 1, 12, 13). Misma filosofía que
# `Divergence` (ADR-005, Decisión 7): la clasificación es el propio tipo
# Python, nunca un string/enum libre en el envelope -- por eso la
# autoridad LOCAL/REMOTE/OBSERVED se codifica como una capa intermedia de
# clases marcadoras, no como un campo configurable: es estructuralmente
# imposible construir un hecho con la autoridad "equivocada".
# ---------------------------------------------------------------------------

class ExecutionLedgerEventPayload:
    """Marcador no instanciable, base de todo payload de evento del
    Execution Ledger. Nunca se instancia directamente."""


class LocalFact(ExecutionLedgerEventPayload):
    """Marcador de autoridad LOCAL: un hecho que Phoenix puede afirmar por
    haberlo realizado/registrado él mismo, sin depender de ninguna
    confirmación del exchange."""


class RemoteFact(ExecutionLedgerEventPayload):
    """Marcador de autoridad REMOTE: un hecho confirmado explícitamente por
    una respuesta del exchange."""


class ObservedFact(ExecutionLedgerEventPayload):
    """Marcador de autoridad OBSERVED: un hecho que Phoenix descubrió
    mediante una lectura posterior del estado remoto, no mediante la
    respuesta original de la llamada que lo originó (si la hubo)."""


@dataclass(frozen=True)
class OrderSubmissionAttempted(LocalFact):
    """Hecho LOCAL: Phoenix inició/registró un intento de envío de esta
    orden -- ADR-010, Decisión 2. Registrado siempre ANTES de la llamada
    remota real.

    NO significa aceptada, rechazada, creada remotamente, enviada con
    éxito, ni entregada. Intent y Attempt colapsan deliberadamente en
    este único hecho: no hay evidencia en el código de una fase de
    intención separada de un intento real.

    `execution_bot_id` es OPCIONAL (ADR-010, resolución de OQ1) -- su
    ausencia no implica "bot desconocido", implica que este evento no
    declara ownership por bot.
    """

    execution_order_id: ExecutionOrderId
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal | None = None
    execution_bot_id: ExecutionBotId | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_positive_decimal(self.quantity, field="quantity")

        if self.price is not None:
            _require_finite_positive_decimal(self.price, field="price")
        # Misma regla de acoplamiento price/order_type ya establecida en
        # ExecutionRequest (contracts.py) -- este hecho registra la misma
        # intención de dominio, no una relajación de ella.
        if self.order_type == "limit" and self.price is None:
            raise ValueError("limit order attempt requires price > 0")
        if self.order_type == "market" and self.price is not None:
            raise ValueError("market order attempt must have price=None")

        if self.execution_bot_id is not None:
            if not isinstance(self.execution_bot_id, ExecutionBotId):
                raise TypeError(
                    f"execution_bot_id must be ExecutionBotId or None, "
                    f"got: {type(self.execution_bot_id).__name__}"
                )


@dataclass(frozen=True)
class OrderSubmissionOutcomeUnknown(LocalFact):
    """Hecho LOCAL: el intento de envío terminó sin que Phoenix pudiera
    determinar el resultado remoto -- ADR-010, Decisión 3.

    NO significa rechazo, éxito, existencia ni ausencia de la orden. Es
    un hecho explícito y distinto del silencio (la ausencia de cualquier
    hecho de resultado) -- preservar esta incertidumbre es lo único que
    permite distinguir "seguimos esperando" de "sabemos que algo falló,
    aunque no sepamos qué hizo Bybit" (hoy esta información se descarta
    por completo, ver ADR-010 F2).

    `reason` es una categoría descriptiva de la indeterminación, nunca
    una decisión (`should_retry` y similares están prohibidos) ni el
    objeto de excepción ni un stack trace crudo.
    """

    execution_order_id: ExecutionOrderId
    reason: str

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.reason, field="reason")
        if self.reason not in _VALID_OUTCOME_UNKNOWN_REASONS:
            raise ValueError(
                f"reason must be one of {sorted(_VALID_OUTCOME_UNKNOWN_REASONS)}, "
                f"got: {self.reason!r}"
            )


@dataclass(frozen=True)
class OrderAcceptedByExchange(RemoteFact):
    """Hecho REMOTE: el exchange confirmó explícitamente la creación de
    esta orden (`ret_code==0`, `orderLinkId` verificado) -- ADR-010,
    Decisión 12.

    `execution_order_id` (identidad Phoenix) y `exchange_order_id`
    (identidad remota) se conservan ambos, nunca intercambiados: el
    segundo jamás sustituye ni actúa como fallback del primero (ADR-005,
    Decisión 4).

    `server_time_ms` preserva el mismo campo ya establecido en el
    read-side (`response.time_ms`, ADR-010 F4) -- no es un timestamp de
    creación de orden, es el tiempo de generación de la respuesta del
    gateway de Bybit.
    """

    execution_order_id: ExecutionOrderId
    exchange_order_id: str
    server_time_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.exchange_order_id, field="exchange_order_id")
        _require_non_negative_int(self.server_time_ms, field="server_time_ms")


@dataclass(frozen=True)
class OrderRejectedByExchange(RemoteFact):
    """Hecho REMOTE: el exchange confirmó explícitamente el rechazo de
    negocio de esta orden (`ret_code` en el conjunto de rechazo
    reconocido) -- ADR-010, Decisión 12.

    NUNCA se usa para timeout, fallo de transporte sin respuesta,
    respuesta malformada, ni resultado desconocido -- esos casos son
    `OrderSubmissionOutcomeUnknown`.

    `ret_code`/`ret_msg` son el motivo de rechazo tal como el exchange lo
    reportó -- información de dominio ya segura (`BybitApiError` los
    expone hoy sin envolver ningún dato sensible). Sin headers/firmas/
    cuerpo HTTP crudo.
    """

    execution_order_id: ExecutionOrderId
    ret_code: int
    ret_msg: str
    server_time_ms: int

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        if isinstance(self.ret_code, bool) or not isinstance(self.ret_code, int):
            raise TypeError(f"ret_code must be int, got: {type(self.ret_code).__name__}")
        _require_non_empty_str(self.ret_msg, field="ret_msg")
        _require_non_negative_int(self.server_time_ms, field="server_time_ms")


@dataclass(frozen=True)
class OrderObservedOpen(ObservedFact):
    """Hecho OBSERVED: Phoenix encontró, mediante una lectura posterior de
    Open Orders, una orden abierta que correlaciona con una
    `ExecutionOrderId` propia (`order_id == orderLinkId`) -- ADR-010,
    Decisión 12.

    No implica que Phoenix haya recibido el ACK original -- OBSERVED y
    REMOTE ACK son autoridades distintas; este hecho nunca se convierte
    en `OrderAcceptedByExchange`.

    LIMITACIÓN EXPLÍCITA (Hito 3.83, ver informe): ADR-010 sólo describe
    el caso correlacionado. El caso de una orden observada NO atribuible
    a Phoenix (`order_id is None` en `ExecutionOpenOrder`, ya modelado
    para Reconciliation V1 como `UnattributedExchangeOpenOrder`) no
    estaba decidido para el Ledger y NO se implementa aquí --
    `execution_order_id` es obligatorio, nunca se sustituye por un valor
    ficticio ni por `exchange_order_id`.

    El resto del payload refleja el estado observado tal cual, mismos
    campos que `ExecutionOpenOrder` (positions/open_orders_contracts.py),
    más `server_time_ms` del snapshot de origen.
    """

    execution_order_id: ExecutionOrderId
    exchange_order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    filled_quantity: Decimal
    status: str
    reduce_only: bool
    server_time_ms: int
    price: Decimal | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_order_id, ExecutionOrderId):
            raise TypeError(
                f"execution_order_id must be ExecutionOrderId, "
                f"got: {type(self.execution_order_id).__name__}"
            )
        _require_non_empty_str(self.exchange_order_id, field="exchange_order_id")
        _require_non_empty_str(self.symbol, field="symbol")
        _require_side(self.side, field="side")
        _require_order_type(self.order_type, field="order_type")
        _require_finite_positive_decimal(self.quantity, field="quantity")

        if not isinstance(self.filled_quantity, Decimal):
            raise TypeError(
                f"filled_quantity must be Decimal, got: {type(self.filled_quantity).__name__}"
            )
        if not self.filled_quantity.is_finite():
            raise ValueError("filled_quantity must be finite")
        if self.filled_quantity < 0:
            raise ValueError(f"filled_quantity must be >= 0, got: {self.filled_quantity}")

        _require_non_empty_str(self.status, field="status")
        if self.status not in _VALID_OPEN_ORDER_STATUSES:
            raise ValueError(
                f"status must be one of {sorted(_VALID_OPEN_ORDER_STATUSES)}, "
                f"got: {self.status!r}"
            )

        if not isinstance(self.reduce_only, bool):
            raise TypeError(f"reduce_only must be bool, got: {type(self.reduce_only).__name__}")

        _require_non_negative_int(self.server_time_ms, field="server_time_ms")

        if self.price is not None:
            if not isinstance(self.price, Decimal):
                raise TypeError(f"price must be Decimal or None, got: {type(self.price).__name__}")
            if not self.price.is_finite():
                raise ValueError("price must be finite")
            if self.price <= 0:
                raise ValueError(f"price must be > 0, got: {self.price}")


# ---------------------------------------------------------------------------
# Envelope -- ADR-010, Decisión 11: 4 campos, cada uno justificado por
# evidencia. Deliberadamente SIN `sequence` (el mecanismo de asignación
# depende de una tecnología de persistencia todavía inexistente, ADR-010
# Decisión 9) y SIN `ExchangeAccountIdentity` (responsabilidad del futuro
# Account Registry, ADR-009 Decisión 7).
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionLedgerEvent:
    """Envelope mínimo de un hecho del Execution Ledger.

    `execution_account_id` es universal y obligatorio -- toda cuenta debe
    poder filtrarse/auditarse sin depender de topología de storage futura
    (ADR-010, Decisión 5). `execution_order_id`, en cambio, NO vive aquí:
    no todo evento tiene una orden asociada, así que vive en el payload
    específico de cada tipo (mismo principio ya aplicado en 3.76/3.77 de
    no añadir campos opcionales al envelope sin necesidad).

    `occurred_at_ms` es el instante LOCAL que el productor del evento
    afirma -- recibido, nunca leído de un reloj dentro de este contrato
    (ADR-010, Decisión 8). Timestamp NO garantiza orden total: dos
    eventos distintos pueden compartir el mismo `occurred_at_ms`
    legítimamente (lección de ADR-006, Decisión 3) -- el mecanismo de
    ordering físico queda deliberadamente fuera de este envelope (ADR-010,
    Decisión 9).

    La autoridad (LOCAL/REMOTE/OBSERVED) NO es un campo de este envelope:
    es una propiedad del tipo de `payload` (ADR-010, Decisión 1) --
    verificable con `isinstance(event.payload, LocalFact | RemoteFact |
    ObservedFact)`, nunca configurable como string libre.
    """

    event_id: ExecutionLedgerEventId
    execution_account_id: ExecutionAccountId
    occurred_at_ms: int
    payload: ExecutionLedgerEventPayload

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
        _require_non_negative_int(self.occurred_at_ms, field="occurred_at_ms")
        if not isinstance(self.payload, ExecutionLedgerEventPayload):
            raise TypeError(
                f"payload must be ExecutionLedgerEventPayload, "
                f"got: {type(self.payload).__name__}"
            )
