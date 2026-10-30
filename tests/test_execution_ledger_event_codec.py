import ast
import dataclasses
import inspect
import json
import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

import pytest

import execution_gateway
import execution_gateway.execution_ledger_event_codec as _codec
import execution_gateway.execution_ledger_event_contracts as _ledger
from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId
from execution_gateway.execution_ledger_event_codec import (
    EncodedLedgerPayload,
    LedgerDecodeError,
    LedgerEncodeError,
    canonical_json,
    decode_payload,
    decode_stored_event,
    encode_payload,
    parse_document_strict,
)
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionBotId,
    ExecutionLedgerEventPayload,
    LocalFact,
    ObservedFact,
    OrderAcceptedByExchange,
    OrderIdentityReportedDuplicateByExchange,
    OrderObservedClosed,
    OrderObservedOpen,
    OrderRejectedByExchange,
    OrderSubmissionAttempted,
    OrderSubmissionOutcomeUnknown,
    RemoteFact,
)
from execution_gateway.execution_ledger_persistence_contracts import StoredExecutionLedgerEvent
from execution_gateway.execution_ledger_persistence_errors import (
    LedgerAppendError,
    LedgerIntegrityError,
    LedgerReadError,
)

_PLATFORM_DIR = str(Path(execution_gateway.__file__).resolve().parent.parent)
_X = "ord_" + "a" * 32
_EXPECTED_TYPES = (
    "OrderSubmissionAttempted", "OrderSubmissionOutcomeUnknown", "OrderAcceptedByExchange",
    "OrderRejectedByExchange", "OrderIdentityReportedDuplicateByExchange", "OrderObservedOpen",
    "OrderObservedClosed",
)
_DECODE_REASONS = (
    "unknown_schema_version", "unknown_event_type", "unexpected_field", "missing_field", "invalid_field_type",
    "invalid_decimal", "invalid_identity", "envelope_mismatch", "invariant_violation", "malformed_document",
)


class _Obj:
    pass


def _oid(suffix="a"):
    return ExecutionOrderId(value="ord_" + suffix * 32)


# ---------------------------------------------------------------------------
# Muestras (fábricas perezosas: nada se construye al importar)
# ---------------------------------------------------------------------------

def _closed(**kw):
    base = dict(
        execution_order_id=_oid(), exchange_order_id="E-1", symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("0.10"), filled_quantity=Decimal("0.10"), filled_value=Decimal("5000.00"),
        remote_status="filled", reduce_only=False, server_time_ms=1_700_000_000_500,
        remote_created_time_ms=1_700_000_000_100, remote_updated_time_ms=1_700_000_000_400,
        price=Decimal("50000.0"), average_price=Decimal("50000.00"), cancel_type=None, reject_reason=None,
    )
    base.update(kw)
    return OrderObservedClosed(**base)


def _open(**kw):
    base = dict(
        execution_order_id=_oid(), exchange_order_id="E-2", symbol="ETHUSDT", side="sell", order_type="limit",
        quantity=Decimal("2.5"), filled_quantity=Decimal("0.5"), status="partially_filled", reduce_only=True,
        server_time_ms=1_700_000_000_600, price=Decimal("3000.5"),
    )
    base.update(kw)
    return OrderObservedOpen(**base)


_SAMPLES = {
    "attempted-market": lambda: OrderSubmissionAttempted(
        execution_order_id=_oid(), symbol="BTCUSDT", side="buy", order_type="market", quantity=Decimal("0.001")),
    "attempted-limit-bot": lambda: OrderSubmissionAttempted(
        execution_order_id=_oid("b"), symbol="ETHUSDT", side="sell", order_type="limit",
        quantity=Decimal("1E+2"), price=Decimal("1E-7"), execution_bot_id=ExecutionBotId(value="bot-ñ-1")),
    "attempted-exotic-decimal": lambda: OrderSubmissionAttempted(
        execution_order_id=_oid("c"), symbol="XUSDT", side="buy", order_type="limit",
        quantity=Decimal("0.30000000000000004"), price=Decimal("5E-324")),
    "attempted-padded-symbol": lambda: OrderSubmissionAttempted(
        execution_order_id=_oid("d"), symbol="  BTC USDT\t", side="sell", order_type="market", quantity=Decimal("2")),
    "unknown-transport": lambda: OrderSubmissionOutcomeUnknown(execution_order_id=_oid(), reason="transport_failure"),
    "unknown-malformed": lambda: OrderSubmissionOutcomeUnknown(execution_order_id=_oid(), reason="malformed_response"),
    "unknown-ambiguous": lambda: OrderSubmissionOutcomeUnknown(
        execution_order_id=_oid(), reason="ambiguous_business_response"),
    "unknown-mismatch": lambda: OrderSubmissionOutcomeUnknown(execution_order_id=_oid(), reason="identity_mismatch"),
    "accepted": lambda: OrderAcceptedByExchange(
        execution_order_id=_oid(), exchange_order_id=" Remote-9 ", server_time_ms=1_700_000_000_123),
    "accepted-zero-time": lambda: OrderAcceptedByExchange(
        execution_order_id=_oid(), exchange_order_id="r", server_time_ms=0),
    "rejected": lambda: OrderRejectedByExchange(
        execution_order_id=_oid(), ret_code=110004, ret_msg="  Insufficient  Balance ", server_time_ms=77),
    "rejected-negative-code": lambda: OrderRejectedByExchange(
        execution_order_id=_oid(), ret_code=-1, ret_msg="x", server_time_ms=1),
    "duplicate": lambda: OrderIdentityReportedDuplicateByExchange(
        execution_order_id=_oid(), ret_code=110072, ret_msg="OrderLinkedID is duplicate", server_time_ms=88),
    "open-limit": lambda: _open(),
    "open-market-no-price": lambda: _open(order_type="market", price=None, status="new", filled_quantity=Decimal("0")),
    "closed-filled-limit": lambda: _closed(),
    "closed-filled-market": lambda: _closed(order_type="market", price=None),
    "closed-cancelled-partial": lambda: _closed(
        remote_status="cancelled", filled_quantity=Decimal("0.04"), filled_value=Decimal("2000.0"),
        average_price=Decimal("50000"), cancel_type="CancelByUser"),
    "closed-cancelled-zero": lambda: _closed(
        remote_status="cancelled", filled_quantity=Decimal("0"), filled_value=Decimal("0"), average_price=None,
        cancel_type="CancelByUser"),
    "closed-rejected": lambda: _closed(
        remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("0E-8"), average_price=None,
        reject_reason="EC_PostOnlyWillTakeLiquidity"),
}
_SAMPLE_IDS = list(_SAMPLES)


def _doc(sample):
    return dict(encode_payload(_SAMPLES[sample]()).document)


def _decode(name, doc, version=1):
    return decode_payload(event_type=name, schema_version=version, document=doc)


def _decode_reason(name, doc, version=1):
    with pytest.raises(LedgerDecodeError) as caught:
        decode_payload(event_type=name, schema_version=version, document=doc)
    return caught.value.reason


def _decimal_fields(payload):
    return {f.name: getattr(payload, f.name) for f in dataclasses.fields(payload)
            if isinstance(getattr(payload, f.name), Decimal)}


# ---------------------------------------------------------------------------
# Registro explícito
# ---------------------------------------------------------------------------

class TestRegistry:
    def test_there_are_exactly_seven_concrete_payload_types_in_the_ledger_module(self):
        found = sorted(
            n for n, o in vars(_ledger).items()
            if isinstance(o, type) and dataclasses.is_dataclass(o) and issubclass(o, ExecutionLedgerEventPayload)
        )
        assert found == sorted(_EXPECTED_TYPES)

    def test_registry_names_are_exactly_the_seven_types(self):
        assert sorted(_codec._REGISTRY) == sorted(_EXPECTED_TYPES)

    @pytest.mark.parametrize("name", _EXPECTED_TYPES)
    def test_registry_class_is_the_ledger_class_with_the_same_name(self, name):
        assert _codec._REGISTRY[name][0] is getattr(_ledger, name)

    @pytest.mark.parametrize("name", _EXPECTED_TYPES)
    def test_registry_fields_match_the_dataclass_fields_in_order(self, name):
        cls, spec = _codec._REGISTRY[name]
        assert [s[0] for s in spec] == [f.name for f in dataclasses.fields(cls)]

    @pytest.mark.parametrize("name", _EXPECTED_TYPES)
    def test_registry_optionality_matches_the_dataclass_defaults(self, name):
        cls, spec = _codec._REGISTRY[name]
        defaults = {f.name: f.default for f in dataclasses.fields(cls)}
        for field_name, _, optional in spec:
            assert optional == (defaults[field_name] is None), (name, field_name)
            assert defaults[field_name] is None or defaults[field_name] is dataclasses.MISSING

    @pytest.mark.parametrize("name", _EXPECTED_TYPES)
    def test_registry_kinds_match_the_annotations(self, name):
        import typing

        cls, spec = _codec._REGISTRY[name]
        hints = typing.get_type_hints(cls)
        expected = {"str": str, "int": int, "bool": bool, "decimal": Decimal,
                    "order_id": ExecutionOrderId, "bot_id": ExecutionBotId}
        for field_name, kind, optional in spec:
            hint = hints[field_name]
            args = [a for a in typing.get_args(hint) if a is not type(None)]
            base = args[0] if args else hint
            assert base is expected[kind], (name, field_name, kind, hint)
            assert optional == (type(None) in typing.get_args(hint)), (name, field_name)

    def test_class_to_name_map_uses_exact_types_only(self):
        assert {cls.__name__: name for cls, name in _codec._NAME_BY_CLASS.items()} == {n: n for n in _EXPECTED_TYPES}

    @pytest.mark.parametrize("marker", [LocalFact, RemoteFact, ObservedFact, ExecutionLedgerEventPayload])
    def test_marker_classes_are_not_registered(self, marker):
        assert marker not in _codec._NAME_BY_CLASS
        assert marker.__name__ not in _codec._REGISTRY

    def test_schema_version_is_one(self):
        assert _codec._SCHEMA_VERSION == 1


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------

class TestRoundTrip:
    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_decode_of_encode_equals_the_original_with_exact_class(self, sample):
        payload = _SAMPLES[sample]()
        enc = encode_payload(payload)
        back = decode_payload(event_type=enc.event_type, schema_version=enc.schema_version, document=enc.document)
        assert back == payload
        assert type(back) is type(payload)

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_every_decimal_keeps_its_exact_tuple(self, sample):
        payload = _SAMPLES[sample]()
        enc = encode_payload(payload)
        back = decode_payload(event_type=enc.event_type, schema_version=1, document=enc.document)
        before, after = _decimal_fields(payload), _decimal_fields(back)
        assert before.keys() == after.keys()
        for name in before:
            assert before[name].as_tuple() == after[name].as_tuple(), name
            assert str(before[name]) == str(after[name]), name

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_metadata_is_the_class_name_version_one_and_the_order_id(self, sample):
        payload = _SAMPLES[sample]()
        enc = encode_payload(payload)
        assert enc.event_type == type(payload).__name__
        assert enc.schema_version == 1
        assert enc.execution_order_id == payload.execution_order_id.value
        assert enc.document["execution_order_id"] == enc.execution_order_id

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_document_has_exactly_the_dataclass_fields_in_order(self, sample):
        payload = _SAMPLES[sample]()
        enc = encode_payload(payload)
        assert list(enc.document) == [f.name for f in dataclasses.fields(payload)]

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_document_contains_only_json_scalars_never_floats_or_decimals(self, sample):
        for name, value in encode_payload(_SAMPLES[sample]()).document.items():
            assert value is None or type(value) in (str, int, bool), (name, type(value))

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_decimals_and_identities_are_strings_in_the_document(self, sample):
        payload = _SAMPLES[sample]()
        doc = encode_payload(payload).document
        for name, value in _decimal_fields(payload).items():
            assert doc[name] == str(value) and type(doc[name]) is str
        assert type(doc["execution_order_id"]) is str

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_optionals_are_explicit_nulls_never_omitted(self, sample):
        payload = _SAMPLES[sample]()
        doc = encode_payload(payload).document
        for f in dataclasses.fields(payload):
            assert f.name in doc
            if getattr(payload, f.name) is None:
                assert doc[f.name] is None

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_canonical_text_survives_a_text_round_trip(self, sample):
        payload = _SAMPLES[sample]()
        enc = encode_payload(payload)
        text = canonical_json(enc.document)
        parsed = parse_document_strict(text)
        assert parsed == dict(enc.document)
        back = decode_payload(event_type=enc.event_type, schema_version=1, document=parsed)
        assert back == payload
        assert canonical_json(encode_payload(back).document) == text

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_encoding_is_deterministic(self, sample):
        a = encode_payload(_SAMPLES[sample]())
        b = encode_payload(_SAMPLES[sample]())
        assert a == b and canonical_json(a.document) == canonical_json(b.document)

    def test_all_seven_types_are_covered_by_the_samples(self):
        assert {type(f()).__name__ for f in _SAMPLES.values()} == set(_EXPECTED_TYPES)


# ---------------------------------------------------------------------------
# Decimal
# ---------------------------------------------------------------------------

_DECIMAL_TEXTS = ["0.10", "0.1", "1E-7", "1E+2", "100", "0E-8", "123.4500", "5E-324", "0.30000000000000004",
                  "1E+16", "9999999999999999999999.999999999999", "0.000001"]


class TestDecimal:
    @pytest.mark.parametrize("text", _DECIMAL_TEXTS)
    def test_each_decimal_survives_with_its_exact_representation(self, text):
        payload = OrderSubmissionAttempted(
            execution_order_id=_oid(), symbol="S", side="buy", order_type="limit",
            quantity=Decimal(text) if Decimal(text) > 0 else Decimal("1"), price=Decimal(text) if Decimal(text) > 0 else Decimal("1"),
        )
        enc = encode_payload(payload)
        back = decode_payload(event_type=enc.event_type, schema_version=1, document=enc.document)
        assert back.quantity.as_tuple() == payload.quantity.as_tuple()
        assert enc.document["quantity"] == str(payload.quantity)

    def test_equal_values_with_different_exponents_stay_distinguishable(self):
        a = encode_payload(OrderSubmissionAttempted(
            execution_order_id=_oid(), symbol="S", side="buy", order_type="market", quantity=Decimal("0.10")))
        b = encode_payload(OrderSubmissionAttempted(
            execution_order_id=_oid(), symbol="S", side="buy", order_type="market", quantity=Decimal("0.1")))
        assert Decimal("0.10") == Decimal("0.1")
        assert a.document["quantity"] != b.document["quantity"]
        assert a != b

    def test_no_normalization_when_encoding(self):
        doc = _doc("closed-filled-limit")
        assert doc["quantity"] == "0.10" and doc["filled_value"] == "5000.00" and doc["price"] == "50000.0"
        assert _doc("attempted-limit-bot")["quantity"] == "1E+2"
        assert _doc("attempted-limit-bot")["price"] == "1E-7"
        assert _doc("closed-rejected")["filled_value"] == "0E-8"

    @pytest.mark.parametrize("text", [
        "1e-7", "+1", "1_000", "١٢", " 1", "1 ", "1.", ".5", "NaN", "sNaN", "Infinity", "-Infinity", "inf", "nan",
        "", "abc", "1,5", "0x10", "1e", "--1", "1.0.0", "00.5", "0.50 ", "1E+007", "1E07", "-0.0e0",
    ])
    def test_decode_rejects_non_canonical_or_non_finite_text(self, text):
        doc = _doc("attempted-market")
        doc["quantity"] = text
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invalid_decimal"

    @pytest.mark.parametrize("value", [1, 0, 1.5, 1e3, True, False, [], {}, b"1", None])
    def test_decode_rejects_every_non_string_for_a_required_decimal(self, value):
        doc = _doc("attempted-market")
        doc["quantity"] = value
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invalid_decimal"

    @pytest.mark.parametrize("value", [1, 1.5, True, []])
    def test_decode_rejects_non_string_for_an_optional_decimal(self, value):
        doc = _doc("attempted-limit-bot")
        doc["price"] = value
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invalid_decimal"

    def test_an_optional_decimal_may_be_null(self):
        doc = _doc("attempted-market")
        assert doc["price"] is None
        assert decode_payload(event_type="OrderSubmissionAttempted", schema_version=1, document=doc).price is None

    def test_a_valid_decimal_string_that_breaks_a_dataclass_invariant_is_invariant_violation(self):
        doc = _doc("attempted-market")
        doc["quantity"] = "0"
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invariant_violation"

    def test_encode_rejects_a_float_in_a_decimal_field(self):
        payload = _SAMPLES["attempted-market"]()
        object.__setattr__(payload, "quantity", 0.001)
        with pytest.raises(TypeError):
            encode_payload(payload)

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("sNaN"), Decimal("Infinity"), Decimal("-Infinity")])
    def test_encode_rejects_non_finite_decimals(self, bad):
        payload = _SAMPLES["attempted-market"]()
        object.__setattr__(payload, "quantity", bad)
        with pytest.raises(ValueError):
            encode_payload(payload)

    def test_the_conversion_never_goes_through_float(self):
        tree = ast.parse(inspect.getsource(_codec))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        assert "float" not in names and "from_float" not in names and "quantize" not in names
        assert "normalize" not in names and "to_integral_value" not in names

    def test_a_decimal_precision_beyond_the_default_context_is_not_rounded(self):
        text = "1." + "1" * 60
        doc = _doc("attempted-market")
        doc["quantity"] = text
        assert str(_decode("OrderSubmissionAttempted", doc).quantity) == text


# ---------------------------------------------------------------------------
# Validación de campos
# ---------------------------------------------------------------------------

_FIELDS = {
    name: [f.name for f in dataclasses.fields(getattr(_ledger, name))] for name in _EXPECTED_TYPES
}
_SAMPLE_FOR_TYPE = {
    "OrderSubmissionAttempted": "attempted-limit-bot", "OrderSubmissionOutcomeUnknown": "unknown-transport",
    "OrderAcceptedByExchange": "accepted", "OrderRejectedByExchange": "rejected",
    "OrderIdentityReportedDuplicateByExchange": "duplicate", "OrderObservedOpen": "open-limit",
    "OrderObservedClosed": "closed-filled-limit",
}
_TYPE_FIELD_PAIRS = [(t, f) for t in _EXPECTED_TYPES for f in _FIELDS[t]]
_PAIR_IDS = [f"{t}.{f}" for t, f in _TYPE_FIELD_PAIRS]


class TestFieldValidation:
    @pytest.mark.parametrize("type_name,field", _TYPE_FIELD_PAIRS, ids=_PAIR_IDS)
    def test_a_missing_field_is_rejected(self, type_name, field):
        doc = _doc(_SAMPLE_FOR_TYPE[type_name])
        del doc[field]
        assert _decode_reason(type_name, doc) == "missing_field"

    @pytest.mark.parametrize("type_name", _EXPECTED_TYPES)
    @pytest.mark.parametrize("extra", ["bogus", "should_retry", "server_time", "EXECUTION_ORDER_ID", ""])
    def test_an_unexpected_field_is_rejected(self, type_name, extra):
        doc = _doc(_SAMPLE_FOR_TYPE[type_name])
        doc[extra] = 1
        assert _decode_reason(type_name, doc) == "unexpected_field"

    @pytest.mark.parametrize("type_name", _EXPECTED_TYPES)
    def test_the_ledger_envelope_fields_do_not_belong_in_the_document(self, type_name):
        for envelope_field in ("event_id", "execution_account_id", "occurred_at_ms", "sequence", "committed_at_ms"):
            doc = _doc(_SAMPLE_FOR_TYPE[type_name])
            doc[envelope_field] = "x"
            assert _decode_reason(type_name, doc) == "unexpected_field"

    @pytest.mark.parametrize("type_name,field", [
        (t, f) for t, f in _TYPE_FIELD_PAIRS
        if f not in ("execution_order_id", "execution_bot_id", "quantity", "price", "filled_quantity",
                     "filled_value", "average_price")
        and f not in ("price", "average_price", "cancel_type", "reject_reason")
    ])
    def test_null_in_a_required_non_decimal_non_identity_field_is_rejected(self, type_name, field):
        doc = _doc(_SAMPLE_FOR_TYPE[type_name])
        doc[field] = None
        assert _decode_reason(type_name, doc) == "invalid_field_type"

    @pytest.mark.parametrize("value", [1, True, None, 1.5, [], {}, b"x"])
    def test_a_str_field_rejects_non_strings(self, value):
        doc = _doc("rejected")
        doc["ret_msg"] = value
        assert _decode_reason("OrderRejectedByExchange", doc) == "invalid_field_type"

    @pytest.mark.parametrize("value", [True, False, 1.0, 5.5, "1", None, [], {}, 1e3])
    def test_an_int_field_rejects_bool_float_and_text(self, value):
        doc = _doc("accepted")
        doc["server_time_ms"] = value
        assert _decode_reason("OrderAcceptedByExchange", doc) == "invalid_field_type"

    def test_an_int_field_accepts_a_real_int_including_huge_values(self):
        doc = _doc("accepted")
        doc["server_time_ms"] = 10**30
        assert _decode("OrderAcceptedByExchange", doc).server_time_ms == 10**30

    def test_a_negative_int_that_violates_the_invariant_is_invariant_violation(self):
        doc = _doc("accepted")
        doc["server_time_ms"] = -1
        assert _decode_reason("OrderAcceptedByExchange", doc) == "invariant_violation"

    @pytest.mark.parametrize("value", [0, 1, "true", "false", None, 1.0, "", []])
    def test_a_bool_field_accepts_only_real_booleans(self, value):
        doc = _doc("open-limit")
        doc["reduce_only"] = value
        assert _decode_reason("OrderObservedOpen", doc) == "invalid_field_type"

    @pytest.mark.parametrize("value", [True, False])
    def test_a_bool_field_round_trips_both_values(self, value):
        doc = _doc("open-limit")
        doc["reduce_only"] = value
        assert _decode("OrderObservedOpen", doc).reduce_only is value

    @pytest.mark.parametrize("value", [
        "ORD_" + "a" * 32, "ord_" + "A" * 32, "ord_" + "a" * 31, "ord_" + "a" * 33, "a" * 36, "", " ", None, 5,
        True, "ord_" + "g" * 32, " ord_" + "a" * 32, "ord_" + "a" * 32 + " ", ["ord_"], "ord_" + "a" * 31 + "\x00",
    ])
    def test_a_malformed_execution_order_id_is_invalid_identity(self, value):
        doc = _doc("accepted")
        doc["execution_order_id"] = value
        assert _decode_reason("OrderAcceptedByExchange", doc) == "invalid_identity"

    @pytest.mark.parametrize("value", ["", "   ", 5, True, ["b"], "bot\x00"])
    def test_a_malformed_bot_id_is_invalid_identity(self, value):
        doc = _doc("attempted-limit-bot")
        doc["execution_bot_id"] = value
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invalid_identity"

    def test_a_null_bot_id_is_valid(self):
        doc = _doc("attempted-limit-bot")
        doc["execution_bot_id"] = None
        assert _decode("OrderSubmissionAttempted", doc).execution_bot_id is None

    @pytest.mark.parametrize("value", [None, 5, True, 1.5, "ord_" + "a" * 32 + "\x00"])
    def test_a_required_identity_cannot_be_null_or_non_string(self, value):
        doc = _doc("unknown-transport")
        doc["execution_order_id"] = value
        assert _decode_reason("OrderSubmissionOutcomeUnknown", doc) == "invalid_identity"

    @pytest.mark.parametrize("bad", [None, "doc", 5, ["a"], ("a",), _Obj(), b"{}", 1.5])
    def test_the_document_must_be_a_mapping(self, bad):
        assert _decode_reason("OrderAcceptedByExchange", bad) == "malformed_document"

    def test_document_keys_must_be_strings(self):
        doc = _doc("accepted")
        doc[1] = "x"
        assert _decode_reason("OrderAcceptedByExchange", doc) == "malformed_document"

    def test_a_frozen_mapping_proxy_is_accepted(self):
        enc = encode_payload(_SAMPLES["accepted"]())
        assert isinstance(enc.document, MappingProxyType)
        assert _decode("OrderAcceptedByExchange", enc.document) == _SAMPLES["accepted"]()

    @pytest.mark.parametrize("value", ["a\x00b", "\ud800", "x\udfffy"])
    def test_stored_text_that_could_not_have_been_written_is_rejected(self, value):
        doc = _doc("rejected")
        doc["ret_msg"] = value
        assert _decode_reason("OrderRejectedByExchange", doc) == "invalid_field_type"

    def test_decoding_never_mutates_the_input_document(self):
        doc = _doc("closed-filled-limit")
        before = dict(doc)
        _decode("OrderObservedClosed", doc)
        assert doc == before


# ---------------------------------------------------------------------------
# Invariantes (la dataclass se re-valida al decodificar)
# ---------------------------------------------------------------------------

class TestInvariantViolation:
    def test_rejected_cannot_carry_the_duplicate_code(self):
        doc = _doc("rejected")
        doc["ret_code"] = 110072
        assert _decode_reason("OrderRejectedByExchange", doc) == "invariant_violation"

    def test_duplicate_must_carry_the_duplicate_code(self):
        doc = _doc("duplicate")
        doc["ret_code"] = 110071
        assert _decode_reason("OrderIdentityReportedDuplicateByExchange", doc) == "invariant_violation"

    def test_unknown_reason_must_be_in_the_closed_set(self):
        doc = _doc("unknown-transport")
        doc["reason"] = "timeout"
        assert _decode_reason("OrderSubmissionOutcomeUnknown", doc) == "invariant_violation"

    def test_closed_filled_requires_full_quantity(self):
        doc = _doc("closed-filled-limit")
        doc["filled_quantity"] = "0.05"
        assert _decode_reason("OrderObservedClosed", doc) == "invariant_violation"

    def test_closed_updated_time_cannot_precede_created_time(self):
        doc = _doc("closed-filled-limit")
        doc["remote_updated_time_ms"] = doc["remote_created_time_ms"] - 1
        assert _decode_reason("OrderObservedClosed", doc) == "invariant_violation"

    def test_attempted_limit_requires_a_price(self):
        doc = _doc("attempted-limit-bot")
        doc["price"] = None
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invariant_violation"

    def test_attempted_side_must_be_valid(self):
        doc = _doc("attempted-market")
        doc["side"] = "hold"
        assert _decode_reason("OrderSubmissionAttempted", doc) == "invariant_violation"

    def test_open_status_must_be_an_open_status(self):
        doc = _doc("open-limit")
        doc["status"] = "filled"
        assert _decode_reason("OrderObservedOpen", doc) == "invariant_violation"

    def test_programming_errors_are_not_wrapped_as_corruption(self):
        with pytest.raises(TypeError):
            decode_payload(schema_version=1, document={})  # falta event_type: error de llamada, no de datos

    def test_unexpected_exceptions_from_the_payload_constructor_propagate(self, monkeypatch):
        class Boom:
            def __init__(self, **kwargs):
                raise RuntimeError("programming defect")

        doc = _doc("accepted")
        _, spec = _codec._REGISTRY["OrderAcceptedByExchange"]
        monkeypatch.setitem(_codec._REGISTRY, "OrderAcceptedByExchange", (Boom, spec))
        with pytest.raises(RuntimeError):
            decode_payload(event_type="OrderAcceptedByExchange", schema_version=1, document=doc)

    def test_the_original_validation_error_is_chained(self):
        doc = _doc("rejected")
        doc["ret_code"] = 110072
        with pytest.raises(LedgerDecodeError) as caught:
            _decode("OrderRejectedByExchange", doc)
        assert isinstance(caught.value.__cause__, ValueError)


# ---------------------------------------------------------------------------
# Versiones y tipos de evento
# ---------------------------------------------------------------------------

class TestVersionsAndEventTypes:
    @pytest.mark.parametrize("version", [0, 2, -1, 10**9, True, False, "1", 1.0, None, [1], b"1"])
    def test_unsupported_schema_versions_fail_closed(self, version):
        assert _decode_reason("OrderAcceptedByExchange", _doc("accepted"), version=version) == "unknown_schema_version"

    @pytest.mark.parametrize("name", [
        "", "orderacceptedbyexchange", "OrderAcceptedByExchange ", " OrderAcceptedByExchange", "LocalFact",
        "RemoteFact", "ObservedFact", "ExecutionLedgerEventPayload", "ExecutionLedgerEvent", "object",
        "OrderRejected", "OrderAccepted", "_REGISTRY", "__class__", "OrderSubmissionAttempted\x00",
        None, 1, True, b"OrderAcceptedByExchange", ["OrderAcceptedByExchange"],
    ])
    def test_unknown_event_types_fail_closed(self, name):
        assert _decode_reason(name, _doc("accepted")) == "unknown_event_type"

    def test_the_version_is_checked_before_the_event_type(self):
        assert _decode_reason("nope", {}, version=2) == "unknown_schema_version"

    def test_the_event_type_is_checked_before_the_document(self):
        assert _decode_reason("nope", "not-a-document") == "unknown_event_type"

    def test_a_document_of_another_type_does_not_decode_as_this_type(self):
        assert _decode_reason("OrderRejectedByExchange", _doc("accepted")) in ("unexpected_field", "missing_field")
        assert _decode_reason("OrderObservedOpen", _doc("closed-filled-limit")) in ("unexpected_field", "missing_field")

    def test_rejected_and_duplicate_documents_share_a_shape_but_not_their_validity(self):
        doc = _doc("duplicate")
        assert _decode_reason("OrderRejectedByExchange", doc) == "invariant_violation"
        doc = _doc("rejected")
        assert _decode_reason("OrderIdentityReportedDuplicateByExchange", doc) == "invariant_violation"


# ---------------------------------------------------------------------------
# Encode: tipos no registrados, texto no almacenable, atomicidad
# ---------------------------------------------------------------------------

class TestEncode:
    def test_a_foreign_class_with_a_registered_name_is_not_registered(self):
        @dataclasses.dataclass(frozen=True)
        class OrderAcceptedByExchange:  # mismo nombre, otra clase: no debe reconocerse por nombre
            execution_order_id: ExecutionOrderId
            exchange_order_id: str
            server_time_ms: int

        impostor = OrderAcceptedByExchange(execution_order_id=_oid(), exchange_order_id="r", server_time_ms=1)
        with pytest.raises(TypeError):
            encode_payload(impostor)

    def test_a_subclass_of_a_registered_type_is_not_registered(self):
        class Sub(OrderAcceptedByExchange):
            pass

        with pytest.raises(TypeError):
            encode_payload(Sub(execution_order_id=_oid(), exchange_order_id="r", server_time_ms=1))

    @pytest.mark.parametrize("make", [
        lambda: None, lambda: "payload", lambda: {"execution_order_id": _X}, lambda: LocalFact(),
        lambda: ExecutionLedgerEventPayload(), lambda: _Obj(), lambda: OrderAcceptedByExchange,
        lambda: ExecutionOrderId(value=_X),
    ], ids=["none", "str", "dict", "marker", "base", "obj", "class", "identity"])
    def test_non_payloads_raise_type_error(self, make):
        with pytest.raises(TypeError):
            encode_payload(make())

    @pytest.mark.parametrize("field,make", [
        ("symbol", lambda: OrderSubmissionAttempted(execution_order_id=_oid(), symbol="BTC\x00USDT", side="buy",
                                                    order_type="market", quantity=Decimal("1"))),
        ("ret_msg", lambda: OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg="a\x00",
                                                    server_time_ms=1)),
        ("exchange_order_id", lambda: OrderAcceptedByExchange(execution_order_id=_oid(), exchange_order_id="\x00",
                                                              server_time_ms=1)),
        ("execution_bot_id", lambda: OrderSubmissionAttempted(
            execution_order_id=_oid(), symbol="S", side="buy", order_type="market", quantity=Decimal("1"),
            execution_bot_id=ExecutionBotId(value="b\x00"))),
    ])
    def test_nul_characters_fail_closed_with_a_typed_encode_error(self, field, make):
        with pytest.raises(LedgerEncodeError) as caught:
            encode_payload(make())
        assert caught.value.reason == "nul_character" and caught.value.field == field

    @pytest.mark.parametrize("text", ["\ud800", "x\udc00y", "\udfff"])
    def test_lone_surrogates_fail_closed_with_a_typed_encode_error(self, text):
        payload = OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg=text, server_time_ms=1)
        with pytest.raises(LedgerEncodeError) as caught:
            encode_payload(payload)
        assert caught.value.reason == "invalid_unicode" and caught.value.field == "ret_msg"

    @pytest.mark.parametrize("text", [
        "ñandú", "日本語", "😀 emoji", "é", "é", "  padded  ", "tab\there", "line\nbreak", "a\u2028b",
        "\ufeff", "퟿", "a" * 10_000, "\u200b", "𝔘𝔫𝔦𝔠𝔬𝔡𝔢",
    ])
    def test_valid_unicode_is_preserved_literally_without_normalization(self, text):
        payload = OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg=text, server_time_ms=1)
        enc = encode_payload(payload)
        assert enc.document["ret_msg"] == text
        wire = parse_document_strict(canonical_json(enc.document))
        back = decode_payload(event_type=enc.event_type, schema_version=1, document=wire)
        assert back.ret_msg == text and back == payload

    def test_composed_and_decomposed_forms_stay_distinct(self):
        a = encode_payload(OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg="é", server_time_ms=1))
        b = encode_payload(OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg="é", server_time_ms=1))
        assert a.document["ret_msg"] != b.document["ret_msg"]

    @pytest.mark.parametrize("field,bad", [
        ("server_time_ms", True), ("server_time_ms", 1.5), ("server_time_ms", "1"), ("ret_code", False),
        ("ret_msg", 5), ("execution_order_id", _X),
    ])
    def test_tampered_payloads_with_wrong_field_types_are_programming_errors(self, field, bad):
        payload = _SAMPLES["rejected"]()
        object.__setattr__(payload, field, bad)
        with pytest.raises(TypeError):
            encode_payload(payload)

    def test_a_required_field_set_to_none_is_a_programming_error(self):
        payload = _SAMPLES["rejected"]()
        object.__setattr__(payload, "ret_msg", None)
        with pytest.raises(TypeError):
            encode_payload(payload)

    def test_a_failing_encode_returns_nothing_and_leaves_the_payload_untouched(self):
        payload = OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg="a\x00", server_time_ms=1)
        before = dataclasses.asdict(payload)
        with pytest.raises(LedgerEncodeError):
            encode_payload(payload)
        assert dataclasses.asdict(payload) == before

    def test_the_encoded_document_is_deeply_frozen(self):
        enc = encode_payload(_SAMPLES["accepted"]())
        assert isinstance(enc.document, MappingProxyType)
        with pytest.raises(TypeError):
            enc.document["server_time_ms"] = 5

    def test_the_encoded_object_is_frozen(self):
        enc = encode_payload(_SAMPLES["accepted"]())
        with pytest.raises(dataclasses.FrozenInstanceError):
            enc.event_type = "x"

    def test_encoding_does_not_generate_or_read_anything_else(self):
        # Mismo payload => mismo resultado: ningún reloj, uuid ni estado oculto.
        assert encode_payload(_SAMPLES["closed-filled-limit"]()) == encode_payload(_SAMPLES["closed-filled-limit"]())


class TestEncodedLedgerPayload:
    def _kw(self, **o):
        kw = dict(event_type="OrderAcceptedByExchange", schema_version=1, execution_order_id=_X,
                  document={"execution_order_id": _X})
        kw.update(o)
        return kw

    def test_constructs_and_freezes_the_document(self):
        source = {"execution_order_id": _X, "nested": {"a": [1, 2]}}
        enc = EncodedLedgerPayload(**self._kw(document=source))
        source["nested"]["a"].append(3)
        assert enc.document["nested"]["a"] == (1, 2)
        assert isinstance(enc.document["nested"], MappingProxyType)

    @pytest.mark.parametrize("o,exc", [
        (dict(event_type=5), TypeError), (dict(event_type="Nope"), ValueError), (dict(event_type="LocalFact"), ValueError),
        (dict(schema_version=True), TypeError), (dict(schema_version="1"), TypeError), (dict(schema_version=2), ValueError),
        (dict(execution_order_id=5), TypeError), (dict(document=[("a", 1)]), TypeError), (dict(document=None), TypeError),
        (dict(execution_order_id="ord_" + "b" * 32), ValueError), (dict(document={}), ValueError),
    ])
    def test_rejects_inconsistent_construction(self, o, exc):
        with pytest.raises(exc):
            EncodedLedgerPayload(**self._kw(**o))

    def test_exact_field_set(self):
        assert [f.name for f in dataclasses.fields(EncodedLedgerPayload)] == [
            "event_type", "schema_version", "execution_order_id", "document",
        ]


# ---------------------------------------------------------------------------
# decode_stored_event
# ---------------------------------------------------------------------------

_EVENT_ID = "3f1c9a52-8d3b-4c5e-9a41-0b7d6e2f1a90"


def _stored_kwargs(sample, **o):
    enc = encode_payload(_SAMPLES[sample]())
    kw = dict(event_id=_EVENT_ID, execution_account_id="acct-1", sequence=7, occurred_at_ms=1_700_000_000_000,
              committed_at_ms=1_700_000_000_050, event_type=enc.event_type, schema_version=enc.schema_version,
              execution_order_id=enc.execution_order_id, document=enc.document)
    kw.update(o)
    return kw


def _stored_reason(sample, **o):
    with pytest.raises(LedgerDecodeError) as caught:
        decode_stored_event(**_stored_kwargs(sample, **o))
    return caught.value.reason


class TestDecodeStoredEvent:
    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_reconstructs_every_column_and_the_payload(self, sample):
        stored = decode_stored_event(**_stored_kwargs(sample))
        assert isinstance(stored, StoredExecutionLedgerEvent)
        assert stored.event.event_id.value == _EVENT_ID
        assert stored.event.execution_account_id == ExecutionAccountId(value="acct-1")
        assert (stored.sequence, stored.event.occurred_at_ms, stored.committed_at_ms) == (
            7, 1_700_000_000_000, 1_700_000_000_050)
        assert stored.event.payload == _SAMPLES[sample]()
        assert type(stored.event.payload) is type(_SAMPLES[sample]())

    def test_occurred_at_and_committed_at_stay_distinct(self):
        stored = decode_stored_event(**_stored_kwargs("accepted", occurred_at_ms=5, committed_at_ms=9))
        assert (stored.event.occurred_at_ms, stored.committed_at_ms) == (5, 9)

    @pytest.mark.parametrize("value", [None, 5, b"x", "", "   ", True])
    def test_invalid_event_id(self, value):
        assert _stored_reason("accepted", event_id=value) == "invalid_identity"

    @pytest.mark.parametrize("value", [None, 5, "", "  ", ExecutionAccountId(value="a"), True])
    def test_invalid_account(self, value):
        assert _stored_reason("accepted", execution_account_id=value) == "invalid_identity"

    @pytest.mark.parametrize("value", [0, -1, True, False, "1", 1.0, None, 1.5])
    def test_invalid_sequence(self, value):
        assert _stored_reason("accepted", sequence=value) == "envelope_mismatch"

    @pytest.mark.parametrize("name", ["occurred_at_ms", "committed_at_ms"])
    @pytest.mark.parametrize("value", [-1, True, "1", 1.0, None])
    def test_invalid_timestamps(self, name, value):
        assert _stored_reason("accepted", **{name: value}) == "envelope_mismatch"

    @pytest.mark.parametrize("name", ["occurred_at_ms", "committed_at_ms"])
    def test_zero_timestamps_are_valid(self, name):
        stored = decode_stored_event(**_stored_kwargs("accepted", **{name: 0}))
        assert stored is not None

    @pytest.mark.parametrize("name,value", [
        ("sequence", 0), ("sequence", -1), ("sequence", True), ("sequence", "1"),
        ("occurred_at_ms", -1), ("occurred_at_ms", True), ("occurred_at_ms", 1.0),
        ("committed_at_ms", -1), ("committed_at_ms", True), ("committed_at_ms", "1"),
    ])
    def test_invalid_envelope_integers_name_the_offending_field(self, name, value):
        with pytest.raises(LedgerDecodeError) as caught:
            decode_stored_event(**_stored_kwargs("accepted", **{name: value}))
        assert (caught.value.reason, caught.value.field) == ("envelope_mismatch", name)

    @pytest.mark.parametrize("value", ["ord_" + "b" * 32, "", None, 5, "ORD_" + "A" * 32])
    def test_denormalized_order_id_must_match_the_document(self, value):
        assert _stored_reason("accepted", execution_order_id=value) == "envelope_mismatch"

    def test_event_type_column_must_match_the_document_shape(self):
        reason = _stored_reason("accepted", event_type="OrderRejectedByExchange")
        assert reason in ("unexpected_field", "missing_field")

    def test_unknown_version_and_type_propagate_from_the_payload_decoder(self):
        assert _stored_reason("accepted", schema_version=2) == "unknown_schema_version"
        assert _stored_reason("accepted", event_type="Nope") == "unknown_event_type"

    def test_corrupt_document_inside_a_stored_event_is_reported_as_decode_error(self):
        doc = dict(encode_payload(_SAMPLES["accepted"]()).document)
        doc["server_time_ms"] = "x"
        assert _stored_reason("accepted", document=doc) == "invalid_field_type"

    def test_arguments_are_keyword_only(self):
        with pytest.raises(TypeError):
            decode_stored_event(_EVENT_ID, "acct-1", 1, 1, 1, "OrderAcceptedByExchange", 1, _X, {})

    def test_the_decode_error_is_an_integrity_error_not_a_read_error(self):
        with pytest.raises(LedgerIntegrityError) as caught:
            decode_stored_event(**_stored_kwargs("accepted", sequence=0))
        assert not isinstance(caught.value, LedgerReadError)


# ---------------------------------------------------------------------------
# parse_document_strict / canonical_json
# ---------------------------------------------------------------------------

class TestParseDocumentStrict:
    def test_parses_a_valid_object(self):
        assert parse_document_strict('{"a":1,"b":"x","c":null,"d":true}') == {"a": 1, "b": "x", "c": None, "d": True}

    @pytest.mark.parametrize("text", [
        '{"a":1,"a":2}', '{"a":1,"b":2,"a":1}', '{"x":{"k":1,"k":2}}',
        '{"a":1.5}', '{"a":1.0}', '{"a":1e3}', '{"a":1E3}', '{"a":-0.0}', '{"a":[1.5]}',
        '{"a":NaN}', '{"a":Infinity}', '{"a":-Infinity}',
        '[]', '"text"', '1', 'null', 'true', '[{"a":1}]', '', '   ', '{', '{"a":1}}', '{"a":1} x', "{'a':1}",
        '\ufeff{"a":1}', '{"a":}', '{"a" 1}', '{a:1}', '{"a":1,}', '{"a":1}{"b":2}',
        '{"a":' + "9" * 5000 + '}',
        "[" * 100000,
        '{"a":' + "[" * 100000 + "]" * 100000 + "}",
    ])
    def test_rejects_malformed_or_non_strict_documents(self, text):
        with pytest.raises(LedgerDecodeError) as caught:
            parse_document_strict(text)
        assert caught.value.reason == "malformed_document"

    @pytest.mark.parametrize("bad", [None, 5, b'{"a":1}', ["a"], _Obj()])
    def test_non_text_is_a_programming_error(self, bad):
        with pytest.raises(TypeError):
            parse_document_strict(bad)

    def test_large_integers_are_accepted_exactly(self):
        assert parse_document_strict('{"a":10000000000000000000000}')["a"] == 10**22

    def test_a_decimal_sent_as_a_json_number_never_reaches_the_event(self):
        text = '{"execution_order_id":"%s","symbol":"S","side":"buy","order_type":"market","quantity":0.001,' \
               '"price":null,"execution_bot_id":null}' % _X
        with pytest.raises(LedgerDecodeError) as caught:
            parse_document_strict(text)
        assert caught.value.reason == "malformed_document"

    def test_escaped_surrogates_parse_but_are_rejected_by_the_field_decoder(self):
        doc = parse_document_strict('{"a":"\\ud800"}')
        assert doc["a"] == "\ud800"
        full = _doc("rejected")
        full["ret_msg"] = doc["a"]
        assert _decode_reason("OrderRejectedByExchange", full) == "invalid_field_type"

    def test_unicode_text_round_trips_through_the_parser(self):
        assert parse_document_strict('{"a":"ñ日本😀"}') == {"a": "ñ日本😀"}


class TestCanonicalJson:
    def test_keys_are_sorted_and_the_separators_compact(self):
        assert canonical_json({"b": 1, "a": [1, {"d": 2, "c": 3}], "z": None}) == '{"a":[1,{"c":3,"d":2}],"b":1,"z":null}'

    def test_unicode_is_emitted_literally_not_escaped(self):
        assert canonical_json({"a": "ñ日本😀"}) == '{"a":"ñ日本😀"}'

    def test_it_is_independent_of_insertion_order(self):
        assert canonical_json({"a": 1, "b": 2}) == canonical_json({"b": 2, "a": 1})

    def test_booleans_are_not_confused_with_integers(self):
        assert canonical_json({"a": True, "b": 1, "c": False, "d": 0}) == '{"a":true,"b":1,"c":false,"d":0}'

    def test_accepts_a_frozen_mapping_proxy(self):
        enc = encode_payload(_SAMPLES["accepted"]())
        assert canonical_json(enc.document) == canonical_json(dict(enc.document))

    @pytest.mark.parametrize("bad", [
        {"a": 1.5}, {"a": 1.0}, {"a": float("nan")}, {"a": float("inf")}, {"a": Decimal("1")}, {"a": b"x"},
        {"a": {1, 2}}, {"a": _Obj()}, {1: "x"}, {"a": {"b": 1.5}}, {"a": [1.5]},
    ])
    def test_rejects_floats_and_non_json_values(self, bad):
        with pytest.raises(TypeError):
            canonical_json(bad)

    @pytest.mark.parametrize("bad", [None, "text", 5, [("a", 1)], _Obj()])
    def test_requires_a_mapping(self, bad):
        with pytest.raises(TypeError):
            canonical_json(bad)

    @pytest.mark.parametrize("bad", [{"a": "x\x00"}, {"a\x00": "x"}, {"a": "\ud800"}, {"a": ["\ud800"]}])
    def test_text_that_cannot_be_stored_is_a_typed_encode_error(self, bad):
        with pytest.raises(LedgerEncodeError):
            canonical_json(bad)

    @pytest.mark.parametrize("sample", _SAMPLE_IDS)
    def test_output_is_valid_utf8_json(self, sample):
        text = canonical_json(encode_payload(_SAMPLES[sample]()).document)
        assert json.loads(text) == dict(encode_payload(_SAMPLES[sample]()).document)
        text.encode("utf-8")


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class TestErrors:
    def test_decode_error_is_an_integrity_error_and_encode_error_an_append_error(self):
        assert issubclass(LedgerDecodeError, LedgerIntegrityError)
        assert issubclass(LedgerEncodeError, LedgerAppendError)
        assert not issubclass(LedgerDecodeError, (LedgerReadError, LedgerAppendError))
        assert not issubclass(LedgerEncodeError, (LedgerReadError, LedgerIntegrityError))

    @pytest.mark.parametrize("reason", _DECODE_REASONS)
    def test_every_decode_reason_is_constructible_and_exposed(self, reason):
        error = LedgerDecodeError(reason=reason, field="f")
        assert error.reason == reason and error.field == "f" and reason in str(error)

    @pytest.mark.parametrize("reason", ["nul_character", "invalid_unicode"])
    def test_every_encode_reason_is_constructible(self, reason):
        assert LedgerEncodeError(reason=reason).reason == reason

    @pytest.mark.parametrize("reason", ["", "other", "UNKNOWN_SCHEMA_VERSION", None, "nul_character"])
    def test_decode_reasons_are_a_closed_set(self, reason):
        with pytest.raises((ValueError, TypeError)):
            LedgerDecodeError(reason=reason)

    @pytest.mark.parametrize("reason", ["", "other", "invalid_decimal", None])
    def test_encode_reasons_are_a_closed_set(self, reason):
        with pytest.raises((ValueError, TypeError)):
            LedgerEncodeError(reason=reason)

    def test_the_closed_sets_are_exactly_the_documented_ones(self):
        assert _codec._DECODE_REASONS == frozenset(_DECODE_REASONS)
        assert _codec._ENCODE_REASONS == frozenset({"nul_character", "invalid_unicode"})

    def test_field_must_be_text_or_none(self):
        with pytest.raises(TypeError):
            LedgerDecodeError(reason="missing_field", field=5)

    def test_messages_never_contain_payload_values(self):
        secret = "SECRET-RET-MSG-VALUE"
        doc = _doc("rejected")
        doc["ret_msg"] = secret
        doc["ret_code"] = 110072
        with pytest.raises(LedgerDecodeError) as caught:
            _decode("OrderRejectedByExchange", doc)
        assert secret not in str(caught.value) and secret not in repr(caught.value)
        payload = OrderRejectedByExchange(execution_order_id=_oid(), ret_code=1, ret_msg=secret + "\x00", server_time_ms=1)
        with pytest.raises(LedgerEncodeError) as caught2:
            encode_payload(payload)
        assert secret not in str(caught2.value)

    def test_arguments_are_keyword_only(self):
        with pytest.raises(TypeError):
            LedgerDecodeError("missing_field")
        with pytest.raises(TypeError):
            LedgerEncodeError("nul_character")


# ---------------------------------------------------------------------------
# Contenido estable: el codec no decide, pero tampoco lo estropea
# ---------------------------------------------------------------------------

class TestStableContentNeutrality:
    @pytest.mark.parametrize("make", [
        lambda **k: _closed(**k), lambda **k: _open(**k),
    ], ids=["closed", "open"])
    def test_observations_differing_only_in_server_time_differ_only_in_that_field(self, make):
        a = encode_payload(make(server_time_ms=1_700_000_000_500))
        b = encode_payload(make(server_time_ms=1_700_000_009_999))
        diff = {k for k in a.document if a.document[k] != b.document[k]}
        assert diff == {"server_time_ms"}
        assert a != b

    def test_server_time_ms_is_an_ordinary_integer_field_with_no_digest_or_hash(self):
        doc = _doc("closed-filled-limit")
        assert type(doc["server_time_ms"]) is int
        assert not any(k in doc for k in ("hash", "digest", "checksum", "stable_content", "content_key"))

    def test_both_observations_decode_to_their_own_server_time(self):
        for t in (1, 2):
            doc = _doc("closed-filled-limit")
            doc["server_time_ms"] = t
            assert _decode("OrderObservedClosed", doc).server_time_ms == t

    def test_economically_equal_but_textually_different_values_are_not_collapsed(self):
        a = encode_payload(_closed(quantity=Decimal("0.10"), filled_quantity=Decimal("0.10")))
        b = encode_payload(_closed(quantity=Decimal("0.1"), filled_quantity=Decimal("0.1")))
        assert a.document["quantity"] != b.document["quantity"]
        assert decode_payload(event_type="OrderObservedClosed", schema_version=1, document=a.document) == \
            decode_payload(event_type="OrderObservedClosed", schema_version=1, document=b.document)

    def test_repeated_open_observations_are_independent_documents(self):
        docs = [encode_payload(_open(filled_quantity=Decimal(q))).document for q in ("0.5", "1.0", "1.5")]
        assert len({canonical_json(d) for d in docs}) == 3


# ---------------------------------------------------------------------------
# Determinismo entre procesos
# ---------------------------------------------------------------------------

class TestCrossProcessDeterminism:
    _SCRIPT = (
        "import sys; sys.path.insert(0, sys.argv[1]);"
        "from decimal import Decimal;"
        "from execution_gateway.execution_identity_contracts import ExecutionOrderId;"
        "from execution_gateway.execution_ledger_event_contracts import OrderObservedClosed, OrderSubmissionAttempted;"
        "from execution_gateway.execution_ledger_event_codec import encode_payload, canonical_json;"
        "x = ExecutionOrderId(value='ord_' + 'a' * 32);"
        "p = OrderSubmissionAttempted(execution_order_id=x, symbol='S', side='buy', order_type='limit',"
        " quantity=Decimal('1E+2'), price=Decimal('0.30000000000000004'));"
        "c = OrderObservedClosed(execution_order_id=x, exchange_order_id='E', symbol='S', side='buy', order_type='limit',"
        " quantity=Decimal('0.10'), filled_quantity=Decimal('0.10'), filled_value=Decimal('5000.00'),"
        " remote_status='filled', reduce_only=False, server_time_ms=5, remote_created_time_ms=1,"
        " remote_updated_time_ms=2, price=Decimal('50000.0'), average_price=Decimal('50000.00'));"
        "print(canonical_json(encode_payload(p).document)); print(canonical_json(encode_payload(c).document))"
    )

    @pytest.mark.parametrize("seed", ["0", "1", "424242", "random"])
    def test_documents_are_identical_across_processes_and_hash_seeds(self, seed):
        out = subprocess.run(
            [sys.executable, "-c", self._SCRIPT, _PLATFORM_DIR], capture_output=True, text=True, check=True,
            env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE="1"), timeout=60,
        ).stdout.splitlines()
        attempted = OrderSubmissionAttempted(
            execution_order_id=ExecutionOrderId(value=_X), symbol="S", side="buy", order_type="limit",
            quantity=Decimal("1E+2"), price=Decimal("0.30000000000000004"))
        closed = _closed(
            exchange_order_id="E", symbol="S", server_time_ms=5, remote_created_time_ms=1, remote_updated_time_ms=2)
        assert out == [canonical_json(encode_payload(attempted).document), canonical_json(encode_payload(closed).document)]


# ---------------------------------------------------------------------------
# Pureza, estructura y exports
# ---------------------------------------------------------------------------

class TestPurityAndStructure:
    def _tree(self):
        return ast.parse(inspect.getsource(_codec))

    def test_imports_are_exactly_stdlib_json_decimal_and_domain_contracts(self):
        names = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        assert names == {
            "json", "collections.abc", "dataclasses", "decimal", "types",
            "execution_gateway.execution_identity_contracts",
            "execution_gateway.execution_ledger_event_contracts",
            "execution_gateway.execution_ledger_persistence_contracts",
            "execution_gateway.execution_ledger_persistence_errors",
        }

    def test_no_clock_uuid_environment_network_vendor_or_dynamic_resolution_names(self):
        tree = self._tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("time", "datetime", "uuid", "uuid4", "environ", "getenv", "socket", "urlopen", "psycopg",
                          "importlib", "__import__", "eval", "exec", "globals", "locals", "random", "os", "sys"):
            assert forbidden not in names, forbidden
        src = inspect.getsource(_codec)
        for forbidden in ("SELECT ", "INSERT ", "pg_advisory", "sqlalchemy"):
            assert forbidden not in src, forbidden

    def test_no_broad_exception_handlers(self):
        handlers = [n for n in ast.walk(self._tree()) if isinstance(n, ast.ExceptHandler)]
        assert handlers
        for h in handlers:
            assert h.type is not None
            assert ast.unparse(h.type) not in ("Exception", "BaseException")
        assert sorted(ast.unparse(h.type) for h in handlers) == sorted([
            "(TypeError, ValueError)", "(TypeError, ValueError)", "(TypeError, ValueError)", "(TypeError, ValueError)",
            "(TypeError, ValueError)", "(ValueError, RecursionError)", "InvalidOperation", "UnicodeEncodeError",
            "UnicodeEncodeError",
        ])

    def test_no_resolution_policy_idempotency_or_stable_content_logic(self):
        public = [n for n in vars(_codec) if not n.startswith("_")]
        for fragment in ("resolv", "stable", "idempot", "block", "halt", "gate", "retry", "compare", "economic"):
            assert not any(fragment in n.lower() for n in public), fragment

    def test_public_surface_is_exactly_the_documented_api(self):
        assert sorted(_codec.__all__) == sorted([
            "EncodedLedgerPayload", "LedgerDecodeError", "LedgerEncodeError", "canonical_json", "decode_payload",
            "decode_stored_event", "encode_payload", "parse_document_strict",
        ])

    def test_functions_are_keyword_only_where_specified(self):
        assert list(inspect.signature(decode_payload).parameters) == ["event_type", "schema_version", "document"]
        for p in inspect.signature(decode_payload).parameters.values():
            assert p.kind is inspect.Parameter.KEYWORD_ONLY
        params = inspect.signature(decode_stored_event).parameters
        assert list(params) == ["event_id", "execution_account_id", "sequence", "occurred_at_ms", "committed_at_ms",
                                "event_type", "schema_version", "execution_order_id", "document"]
        assert all(p.kind is inspect.Parameter.KEYWORD_ONLY for p in params.values())

    @pytest.mark.parametrize("name", [
        "EncodedLedgerPayload", "LedgerDecodeError", "LedgerEncodeError", "canonical_json", "decode_payload",
        "decode_stored_event", "encode_payload", "parse_document_strict",
    ])
    def test_exported_from_package(self, name):
        assert getattr(execution_gateway, name) is getattr(_codec, name)
        assert name in execution_gateway.__all__
