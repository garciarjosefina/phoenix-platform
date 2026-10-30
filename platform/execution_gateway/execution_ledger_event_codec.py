import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from types import MappingProxyType

from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionBotId,
    ExecutionLedgerEvent,
    ExecutionLedgerEventId,
    OrderAcceptedByExchange,
    OrderIdentityReportedDuplicateByExchange,
    OrderObservedClosed,
    OrderObservedOpen,
    OrderRejectedByExchange,
    OrderSubmissionAttempted,
    OrderSubmissionOutcomeUnknown,
)
from execution_gateway.execution_ledger_persistence_contracts import StoredExecutionLedgerEvent
from execution_gateway.execution_ledger_persistence_errors import LedgerAppendError, LedgerIntegrityError

# Codec puro, determinista y reversible de los payloads del Execution Ledger
# (Hito 3.99, ADR-011 D13/D14, ADR-017 D6/D7). Convierte cada payload en
# `(event_type, schema_version, document)` y reconstruye el payload (o el
# `StoredExecutionLedgerEvent`) desde columnas + documento, RE-VALIDANDO todo.
#
# NO es storage ni política: no escribe, no lee, no genera identidades ni
# tiempos, no decide idempotencia, contenido estable, resolución ni bloqueo.
# El `server_time_ms` se almacena como un campo ordinario del documento.
#
# Hay exactamente SIETE tipos concretos de payload (errata de ADR-017 D6, que
# dice "8"): se enumeran explícitamente abajo, sin resolución dinámica.

_SCHEMA_VERSION = 1

# Razones cerradas (diseño forense del Hito 3.99).
_DECODE_REASONS = frozenset({
    "unknown_schema_version",
    "unknown_event_type",
    "unexpected_field",
    "missing_field",
    "invalid_field_type",
    "invalid_decimal",
    "invalid_identity",
    "envelope_mismatch",
    "invariant_violation",
    "malformed_document",
})
_ENCODE_REASONS = frozenset({"nul_character", "invalid_unicode"})

# Clases de campo -> cómo se codifican/decodifican.
_STR, _INT, _BOOL, _DECIMAL, _ORDER_ID, _BOT_ID = "str", "int", "bool", "decimal", "order_id", "bot_id"

# (nombre, clase, opcional). El orden es el de la dataclass; un test fija que
# este registro coincide con `dataclasses.fields` de cada clase.
_REGISTRY: dict[str, tuple[type, tuple[tuple[str, str, bool], ...]]] = {
    "OrderSubmissionAttempted": (OrderSubmissionAttempted, (
        ("execution_order_id", _ORDER_ID, False),
        ("symbol", _STR, False),
        ("side", _STR, False),
        ("order_type", _STR, False),
        ("quantity", _DECIMAL, False),
        ("price", _DECIMAL, True),
        ("execution_bot_id", _BOT_ID, True),
    )),
    "OrderSubmissionOutcomeUnknown": (OrderSubmissionOutcomeUnknown, (
        ("execution_order_id", _ORDER_ID, False),
        ("reason", _STR, False),
    )),
    "OrderAcceptedByExchange": (OrderAcceptedByExchange, (
        ("execution_order_id", _ORDER_ID, False),
        ("exchange_order_id", _STR, False),
        ("server_time_ms", _INT, False),
    )),
    "OrderRejectedByExchange": (OrderRejectedByExchange, (
        ("execution_order_id", _ORDER_ID, False),
        ("ret_code", _INT, False),
        ("ret_msg", _STR, False),
        ("server_time_ms", _INT, False),
    )),
    "OrderIdentityReportedDuplicateByExchange": (OrderIdentityReportedDuplicateByExchange, (
        ("execution_order_id", _ORDER_ID, False),
        ("ret_code", _INT, False),
        ("ret_msg", _STR, False),
        ("server_time_ms", _INT, False),
    )),
    "OrderObservedOpen": (OrderObservedOpen, (
        ("execution_order_id", _ORDER_ID, False),
        ("exchange_order_id", _STR, False),
        ("symbol", _STR, False),
        ("side", _STR, False),
        ("order_type", _STR, False),
        ("quantity", _DECIMAL, False),
        ("filled_quantity", _DECIMAL, False),
        ("status", _STR, False),
        ("reduce_only", _BOOL, False),
        ("server_time_ms", _INT, False),
        ("price", _DECIMAL, True),
    )),
    "OrderObservedClosed": (OrderObservedClosed, (
        ("execution_order_id", _ORDER_ID, False),
        ("exchange_order_id", _STR, False),
        ("symbol", _STR, False),
        ("side", _STR, False),
        ("order_type", _STR, False),
        ("quantity", _DECIMAL, False),
        ("filled_quantity", _DECIMAL, False),
        ("filled_value", _DECIMAL, False),
        ("remote_status", _STR, False),
        ("reduce_only", _BOOL, False),
        ("server_time_ms", _INT, False),
        ("remote_created_time_ms", _INT, False),
        ("remote_updated_time_ms", _INT, False),
        ("price", _DECIMAL, True),
        ("average_price", _DECIMAL, True),
        ("cancel_type", _STR, True),
        ("reject_reason", _STR, True),
    )),
}
# Tipo EXACTO -> nombre. Una subclase o un marcador no están registrados.
_NAME_BY_CLASS: dict[type, str] = {cls: name for name, (cls, _) in _REGISTRY.items()}


class LedgerDecodeError(LedgerIntegrityError):
    """Corrupción de lo ALMACENADO: el documento/columnas no decodifican a un
    evento válido. "Sé, y está mal" -- nunca un fallo de lectura. `reason`
    pertenece a un conjunto cerrado; `field` (opcional) nombra el campo, nunca
    su valor (los mensajes no contienen datos del payload)."""

    def __init__(self, *, reason: str, field: str | None = None) -> None:
        if reason not in _DECODE_REASONS:
            raise ValueError(f"reason must be one of {sorted(_DECODE_REASONS)}, got: {reason!r}")
        if field is not None and not isinstance(field, str):
            raise TypeError(f"field must be str or None, got: {type(field).__name__}")
        suffix = f" (field: {field})" if field else ""
        super().__init__(message=f"ledger decode failed: {reason}{suffix}")
        self.reason = reason
        self.field = field


class LedgerEncodeError(LedgerAppendError):
    """Un payload VÁLIDO que no puede almacenarse tal cual (texto con NUL o
    con un surrogate no codificable). Fail-closed: sin receipt no hay envío.
    No es un error de programación ni corrupción."""

    def __init__(self, *, reason: str, field: str | None = None) -> None:
        if reason not in _ENCODE_REASONS:
            raise ValueError(f"reason must be one of {sorted(_ENCODE_REASONS)}, got: {reason!r}")
        if field is not None and not isinstance(field, str):
            raise TypeError(f"field must be str or None, got: {type(field).__name__}")
        suffix = f" (field: {field})" if field else ""
        super().__init__(message=f"ledger encode failed: {reason}{suffix}")
        self.reason = reason
        self.field = field


def _freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze(v) for v in value)
    return value


@dataclass(frozen=True)
class EncodedLedgerPayload:
    """Resultado de `encode_payload`: lo que el Writer persiste en las
    columnas `event_type`, `schema_version`, `execution_order_id` y `payload`.
    `execution_order_id` es el índice desnormalizado derivado del documento:
    una sola fuente, verificada en la construcción y de nuevo al decodificar.
    `document` queda congelado en profundidad."""

    event_type: str
    schema_version: int
    execution_order_id: str
    document: Mapping

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str):
            raise TypeError(f"event_type must be str, got: {type(self.event_type).__name__}")
        if self.event_type not in _REGISTRY:
            raise ValueError(f"event_type is not a registered ledger payload type: {self.event_type!r}")
        if type(self.schema_version) is not int:
            raise TypeError(f"schema_version must be int, got: {type(self.schema_version).__name__}")
        if self.schema_version != _SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {_SCHEMA_VERSION}, got: {self.schema_version}")
        if not isinstance(self.execution_order_id, str):
            raise TypeError(
                f"execution_order_id must be str, got: {type(self.execution_order_id).__name__}"
            )
        if not isinstance(self.document, Mapping):
            raise TypeError(f"document must be a Mapping, got: {type(self.document).__name__}")
        if self.document.get("execution_order_id") != self.execution_order_id:
            raise ValueError("execution_order_id must equal document['execution_order_id']")
        object.__setattr__(self, "document", _freeze(self.document))


# ---------------------------------------------------------------------------
# Texto representable
# ---------------------------------------------------------------------------

def _check_text_encodable(value: str, *, field: str) -> None:
    # PostgreSQL `jsonb`/`text` rechaza U+0000 y UTF-8 rechaza surrogates:
    # fallar cerrado en lugar de inventar un escape (diseño 3.99, D1).
    if "\x00" in value:
        raise LedgerEncodeError(reason="nul_character", field=field)
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise LedgerEncodeError(reason="invalid_unicode", field=field) from error


def _text_is_storable(value: str) -> bool:
    if "\x00" in value:
        return False
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        return False
    return True


# ---------------------------------------------------------------------------
# Encode
# ---------------------------------------------------------------------------

def _encode_value(value, kind: str, optional: bool, *, field: str):
    if value is None:
        if optional:
            return None
        raise TypeError(f"{field} must not be None")
    if kind == _STR:
        if type(value) is not str:
            raise TypeError(f"{field} must be str, got: {type(value).__name__}")
        _check_text_encodable(value, field=field)
        return value
    if kind == _INT:
        if type(value) is not int:
            raise TypeError(f"{field} must be int, got: {type(value).__name__}")
        return value
    if kind == _BOOL:
        if type(value) is not bool:
            raise TypeError(f"{field} must be bool, got: {type(value).__name__}")
        return value
    if kind == _DECIMAL:
        if not isinstance(value, Decimal):
            raise TypeError(f"{field} must be Decimal, got: {type(value).__name__}")
        if not value.is_finite():
            raise ValueError(f"{field} must be finite")
        return str(value)
    if kind == _ORDER_ID:
        if not isinstance(value, ExecutionOrderId):
            raise TypeError(f"{field} must be ExecutionOrderId, got: {type(value).__name__}")
        _check_text_encodable(value.value, field=field)
        return value.value
    if kind == _BOT_ID:
        if not isinstance(value, ExecutionBotId):
            raise TypeError(f"{field} must be ExecutionBotId, got: {type(value).__name__}")
        _check_text_encodable(value.value, field=field)
        return value.value
    raise AssertionError(f"unknown field kind: {kind}")  # pragma: no cover


def encode_payload(payload) -> EncodedLedgerPayload:
    """Codifica un payload registrado. Atómico: construye el documento
    completo antes de devolver; cualquier fallo levanta sin resultado parcial.

    - Tipo no registrado (incluye subclases y marcadores): `TypeError`
      (error de programación).
    - Payload válido pero no almacenable (NUL / surrogate): `LedgerEncodeError`.
    - Todo campo `Decimal` se codifica como string `str(d)` (exacto, conserva
      el exponente); nunca como número ni vía `float`.
    """
    name = _NAME_BY_CLASS.get(type(payload))
    if name is None:
        raise TypeError(f"payload type is not a registered ledger payload: {type(payload).__name__}")
    _, fields_spec = _REGISTRY[name]
    document: dict[str, object] = {}
    for field_name, kind, optional in fields_spec:
        document[field_name] = _encode_value(getattr(payload, field_name), kind, optional, field=field_name)
    return EncodedLedgerPayload(
        event_type=name,
        schema_version=_SCHEMA_VERSION,
        execution_order_id=document["execution_order_id"],
        document=document,
    )


# ---------------------------------------------------------------------------
# Decode
# ---------------------------------------------------------------------------

def _decode_value(value, kind: str, optional: bool, *, field: str):
    if value is None:
        if optional:
            return None
        raise LedgerDecodeError(reason="invalid_decimal" if kind == _DECIMAL else
                                "invalid_identity" if kind in (_ORDER_ID, _BOT_ID) else "invalid_field_type",
                                field=field)
    if kind == _STR:
        if type(value) is not str or not _text_is_storable(value):
            raise LedgerDecodeError(reason="invalid_field_type", field=field)
        return value
    if kind == _INT:
        if type(value) is not int:
            raise LedgerDecodeError(reason="invalid_field_type", field=field)
        return value
    if kind == _BOOL:
        if type(value) is not bool:
            raise LedgerDecodeError(reason="invalid_field_type", field=field)
        return value
    if kind == _DECIMAL:
        if type(value) is not str:
            raise LedgerDecodeError(reason="invalid_decimal", field=field)
        try:
            decoded = Decimal(value)
        except InvalidOperation as error:
            raise LedgerDecodeError(reason="invalid_decimal", field=field) from error
        # Sólo la forma canónica `str(Decimal)` es válida: rechaza "1e-7",
        # "+1", "1_000", dígitos no ASCII, espacios, "1.", NaN e Infinity.
        if not decoded.is_finite() or str(decoded) != value:
            raise LedgerDecodeError(reason="invalid_decimal", field=field)
        return decoded
    if kind in (_ORDER_ID, _BOT_ID):
        if type(value) is not str or not _text_is_storable(value):
            raise LedgerDecodeError(reason="invalid_identity", field=field)
        try:
            return ExecutionOrderId(value=value) if kind == _ORDER_ID else ExecutionBotId(value=value)
        except (TypeError, ValueError) as error:
            raise LedgerDecodeError(reason="invalid_identity", field=field) from error
    raise AssertionError(f"unknown field kind: {kind}")  # pragma: no cover


def decode_payload(*, event_type, schema_version, document):
    """Reconstruye el payload desde `event_type`, `schema_version` y el
    documento, validando TODO: versión, tipo, claves exactas, tipos JSON,
    forma canónica de cada `Decimal`, identidades y, al reconstruir la
    dataclass, todas sus invariantes. Cualquier problema de lo almacenado
    levanta `LedgerDecodeError` con una razón cerrada. No normaliza nada."""
    if type(schema_version) is not int or schema_version != _SCHEMA_VERSION:
        raise LedgerDecodeError(reason="unknown_schema_version")
    if type(event_type) is not str or event_type not in _REGISTRY:
        raise LedgerDecodeError(reason="unknown_event_type")
    cls, fields_spec = _REGISTRY[event_type]
    if not isinstance(document, Mapping):
        raise LedgerDecodeError(reason="malformed_document")
    if not all(type(key) is str for key in document):
        raise LedgerDecodeError(reason="malformed_document")
    expected = [name for name, _, _ in fields_spec]
    extra = sorted(set(document) - set(expected))
    if extra:
        raise LedgerDecodeError(reason="unexpected_field", field=extra[0])
    for name in expected:
        if name not in document:
            raise LedgerDecodeError(reason="missing_field", field=name)
    kwargs = {
        name: _decode_value(document[name], kind, optional, field=name)
        for name, kind, optional in fields_spec
    }
    try:
        return cls(**kwargs)
    except (TypeError, ValueError) as error:
        raise LedgerDecodeError(reason="invariant_violation") from error


def decode_stored_event(
    *,
    event_id,
    execution_account_id,
    sequence,
    occurred_at_ms,
    committed_at_ms,
    event_type,
    schema_version,
    execution_order_id,
    document,
) -> StoredExecutionLedgerEvent:
    """Reconstruye un `StoredExecutionLedgerEvent` desde las columnas y el
    documento leídos, verificando la consistencia del envelope: identidades
    válidas, enteros del envelope bien formados y `execution_order_id`
    desnormalizado igual al del documento (una divergencia es corrupción
    `envelope_mismatch`). No consulta ni genera nada."""
    if type(event_id) is not str:
        raise LedgerDecodeError(reason="invalid_identity", field="event_id")
    if type(execution_account_id) is not str:
        raise LedgerDecodeError(reason="invalid_identity", field="execution_account_id")
    try:
        event_id_value = ExecutionLedgerEventId(value=event_id)
    except (TypeError, ValueError) as error:
        raise LedgerDecodeError(reason="invalid_identity", field="event_id") from error
    try:
        account_value = ExecutionAccountId(value=execution_account_id)
    except (TypeError, ValueError) as error:
        raise LedgerDecodeError(reason="invalid_identity", field="execution_account_id") from error
    for name, value, minimum in (
        ("sequence", sequence, 1),
        ("occurred_at_ms", occurred_at_ms, 0),
        ("committed_at_ms", committed_at_ms, 0),
    ):
        if type(value) is not int or value < minimum:
            raise LedgerDecodeError(reason="envelope_mismatch", field=name)
    if type(execution_order_id) is not str:
        raise LedgerDecodeError(reason="envelope_mismatch", field="execution_order_id")
    payload = decode_payload(event_type=event_type, schema_version=schema_version, document=document)
    if payload.execution_order_id.value != execution_order_id:
        raise LedgerDecodeError(reason="envelope_mismatch", field="execution_order_id")
    try:
        event = ExecutionLedgerEvent(
            event_id=event_id_value,
            execution_account_id=account_value,
            occurred_at_ms=occurred_at_ms,
            payload=payload,
        )
        return StoredExecutionLedgerEvent(event=event, sequence=sequence, committed_at_ms=committed_at_ms)
    except (TypeError, ValueError) as error:
        raise LedgerDecodeError(reason="envelope_mismatch") from error


# ---------------------------------------------------------------------------
# JSON canónico y parser estricto
# ---------------------------------------------------------------------------

def _plain(value, *, field: str):
    if value is None or type(value) in (bool, int):
        return value
    if type(value) is str:
        _check_text_encodable(value, field=field)
        return value
    if isinstance(value, Mapping):
        out = {}
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"document keys must be str, got: {type(key).__name__}")
            _check_text_encodable(key, field=key)
            out[key] = _plain(item, field=key)
        return out
    if isinstance(value, (list, tuple)):
        return [_plain(item, field=field) for item in value]
    raise TypeError(f"value is not representable as canonical JSON: {type(value).__name__}")


def canonical_json(document) -> str:
    """Texto canónico de un documento: claves ordenadas, sin espacios,
    Unicode literal (UTF-8), sin NaN/Infinity. Determinista; sirve para tests,
    diagnóstico y comparación de formas — NO es una promesa sobre los bytes de
    `jsonb`, que reordena claves y normaliza espacios. Rechaza `float` y
    cualquier tipo no JSON con `TypeError`, y texto con NUL/surrogates con
    `LedgerEncodeError`."""
    if not isinstance(document, Mapping):
        raise TypeError(f"document must be a Mapping, got: {type(document).__name__}")
    return json.dumps(
        _plain(document, field="document"),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


class _MalformedJson(ValueError):
    pass


def _reject_float(text: str):
    raise _MalformedJson("non-integer JSON numbers are not allowed")


def _reject_constant(text: str):
    raise _MalformedJson("NaN/Infinity are not allowed")


def _no_duplicates(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise _MalformedJson("duplicate key")
        out[key] = value
    return out


def parse_document_strict(text: str) -> dict:
    """Parsea el texto JSON de un documento con reglas estrictas: raíz objeto,
    sin claves duplicadas, sin NaN/Infinity y sin números no enteros (todo
    `Decimal` viaja como string). Cualquier problema ⇒ `LedgerDecodeError`
    (`malformed_document`). Sólo parsea: no valida campos ni tipos de evento."""
    if not isinstance(text, str):
        raise TypeError(f"text must be str, got: {type(text).__name__}")
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (ValueError, RecursionError) as error:
        raise LedgerDecodeError(reason="malformed_document") from error
    if type(parsed) is not dict:
        raise LedgerDecodeError(reason="malformed_document")
    return parsed


__all__ = [
    "EncodedLedgerPayload",
    "LedgerDecodeError",
    "LedgerEncodeError",
    "canonical_json",
    "decode_payload",
    "decode_stored_event",
    "encode_payload",
    "parse_document_strict",
]
