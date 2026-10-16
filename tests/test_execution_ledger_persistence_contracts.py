import ast
import dataclasses
import inspect
import typing
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.execution_ledger_persistence_contracts as _module
from execution_gateway.execution_identity_contracts import ExecutionAccountId, ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionLedgerEvent,
    ExecutionLedgerEventId,
    ExecutionLedgerEventPayload,
    OrderObservedOpen,
    OrderSubmissionAttempted,
)
from execution_gateway.execution_ledger_persistence_contracts import (
    AppendReceipt,
    ExecutionLedgerReader,
    ExecutionLedgerWriter,
    StoredExecutionLedgerEvent,
)

_ACCOUNT = ExecutionAccountId(value="acct-1")
_OTHER_ACCOUNT = ExecutionAccountId(value="acct-2")
_EVENT_ID = ExecutionLedgerEventId(value="3f1c9a52-8d3b-4c5e-9a41-0b7d6e2f1a90")
_ORDER = ExecutionOrderId(value="ord_" + "a" * 32)


class _Obj:
    pass


def _receipt(**overrides):
    kw = dict(event_id=_EVENT_ID, execution_account_id=_ACCOUNT, sequence=7, committed_at_ms=1_700_000_000_123)
    kw.update(overrides)
    return AppendReceipt(**kw)


def _event():
    return ExecutionLedgerEvent(
        event_id=_EVENT_ID,
        execution_account_id=_ACCOUNT,
        occurred_at_ms=1_700_000_000_000,
        payload=OrderSubmissionAttempted(
            execution_order_id=_ORDER, symbol="BTCUSDT", side="buy", order_type="market", quantity=Decimal("0.001"),
        ),
    )


def _stored(**overrides):
    kw = dict(event=_event(), sequence=3, committed_at_ms=1_700_000_000_050)
    kw.update(overrides)
    return StoredExecutionLedgerEvent(**kw)


def _members(proto):
    return sorted(n for n in vars(proto) if not n.startswith("_"))


# ---------------------------------------------------------------------------
# AppendReceipt
# ---------------------------------------------------------------------------

class TestAppendReceipt:
    def test_constructs_and_preserves_every_field(self):
        r = _receipt(sequence=42, committed_at_ms=999)
        assert r.event_id is _EVENT_ID
        assert r.execution_account_id is _ACCOUNT
        assert (r.sequence, r.committed_at_ms) == (42, 999)

    def test_exact_field_set_and_order(self):
        assert [f.name for f in dataclasses.fields(AppendReceipt)] == [
            "event_id", "execution_account_id", "sequence", "committed_at_ms",
        ]

    def test_no_field_has_a_default(self):
        for f in dataclasses.fields(AppendReceipt):
            assert f.default is dataclasses.MISSING and f.default_factory is dataclasses.MISSING

    def test_is_frozen(self):
        r = _receipt()
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.sequence = 8
        assert AppendReceipt.__dataclass_params__.frozen

    def test_public_surface_is_exactly_the_fields(self):
        r = _receipt()
        public = {n for n in dir(r) if not n.startswith("_") and not callable(getattr(r, n))}
        assert public == {"event_id", "execution_account_id", "sequence", "committed_at_ms"}

    def test_carries_no_payload_no_domain_time_no_storage_ids_and_no_global_sequence(self):
        r = _receipt()
        for forbidden in ("payload", "occurred_at_ms", "execution_order_id", "row_id", "id", "global_sequence",
                          "lsn", "xid", "event", "event_type"):
            assert not hasattr(r, forbidden), forbidden

    @pytest.mark.parametrize("bad", ["3f1c9a52", None, 1, _ACCOUNT, _ORDER, _Obj(), b"x"])
    def test_event_id_must_be_an_execution_ledger_event_id(self, bad):
        with pytest.raises(TypeError):
            _receipt(event_id=bad)

    @pytest.mark.parametrize("bad", ["acct-1", None, 1, _EVENT_ID, _ORDER, _Obj()])
    def test_execution_account_id_must_be_an_execution_account_id(self, bad):
        with pytest.raises(TypeError):
            _receipt(execution_account_id=bad)

    @pytest.mark.parametrize("bad", [True, False, None, "1", 1.0, 1.5, Decimal("1"), [], b"1", _Obj()])
    def test_sequence_rejects_non_int_and_bool(self, bad):
        with pytest.raises(TypeError):
            _receipt(sequence=bad)

    @pytest.mark.parametrize("bad", [0, -1, -(2**63)])
    def test_sequence_must_be_at_least_one(self, bad):
        with pytest.raises(ValueError):
            _receipt(sequence=bad)

    def test_sequence_one_and_bigint_max_are_valid(self):
        assert _receipt(sequence=1).sequence == 1
        assert _receipt(sequence=2**63 - 1).sequence == 2**63 - 1

    @pytest.mark.parametrize("bad", [True, False, None, "1", 1.0, 1.5, Decimal("1"), [], b"1", _Obj()])
    def test_committed_at_ms_rejects_non_int_and_bool(self, bad):
        with pytest.raises(TypeError):
            _receipt(committed_at_ms=bad)

    def test_committed_at_ms_rejects_negative_and_accepts_zero(self):
        with pytest.raises(ValueError):
            _receipt(committed_at_ms=-1)
        assert _receipt(committed_at_ms=0).committed_at_ms == 0

    def test_sequences_of_different_accounts_are_independent(self):
        # ADR-011 D4: orden total POR cuenta; ninguna continuidad global.
        a = _receipt(execution_account_id=_ACCOUNT, sequence=1)
        b = _receipt(execution_account_id=_OTHER_ACCOUNT, sequence=1)
        assert a.sequence == b.sequence == 1 and a != b

    def test_sequence_and_committed_at_are_not_interchangeable(self):
        r = _receipt(sequence=5, committed_at_ms=500)
        assert (r.sequence, r.committed_at_ms) != (r.committed_at_ms, r.sequence)

    def test_equality_and_hash_are_by_value(self):
        assert _receipt() == _receipt() and hash(_receipt()) == hash(_receipt())
        assert _receipt() != _receipt(sequence=8)


# ---------------------------------------------------------------------------
# StoredExecutionLedgerEvent
# ---------------------------------------------------------------------------

class TestStoredExecutionLedgerEvent:
    def test_constructs_and_preserves_every_field(self):
        event = _event()
        s = StoredExecutionLedgerEvent(event=event, sequence=9, committed_at_ms=11)
        assert s.event is event and (s.sequence, s.committed_at_ms) == (9, 11)

    def test_exact_field_set_and_frozen(self):
        assert [f.name for f in dataclasses.fields(StoredExecutionLedgerEvent)] == [
            "event", "sequence", "committed_at_ms",
        ]
        with pytest.raises(dataclasses.FrozenInstanceError):
            _stored().sequence = 9

    # Las instancias se construyen DENTRO del test (factories perezosas): si
    # `AppendReceipt` se rompiera, falla este test -- no la colección de todo
    # el archivo, que enmascararía el resto (lección de 3.95/3.94).
    @pytest.mark.parametrize("make_bad", [
        lambda: None,
        lambda: "event",
        lambda: 1,
        lambda: _receipt(),
        lambda: OrderObservedOpen,
        lambda: _Obj(),
    ], ids=["none", "str", "int", "receipt", "payload-class", "obj"])
    def test_event_must_be_an_execution_ledger_event(self, make_bad):
        bad = make_bad()
        with pytest.raises(TypeError):
            _stored(event=bad)

    def test_a_bare_payload_is_not_an_event(self):
        with pytest.raises(TypeError):
            _stored(event=_event().payload)

    @pytest.mark.parametrize("bad", [True, None, "1", 1.0, Decimal("1")])
    def test_sequence_rejects_non_int_and_bool(self, bad):
        with pytest.raises(TypeError):
            _stored(sequence=bad)

    def test_sequence_must_be_at_least_one(self):
        for bad in (0, -1):
            with pytest.raises(ValueError):
                _stored(sequence=bad)

    @pytest.mark.parametrize("bad", [True, None, "1", 1.0])
    def test_committed_at_rejects_non_int_and_bool(self, bad):
        with pytest.raises(TypeError):
            _stored(committed_at_ms=bad)

    def test_committed_at_rejects_negative(self):
        with pytest.raises(ValueError):
            _stored(committed_at_ms=-1)

    def test_has_no_mutation_or_policy_surface(self):
        s = _stored()
        for forbidden in ("update", "delete", "replace", "is_resolved", "is_terminal", "receipt", "payload"):
            assert not hasattr(s, forbidden), forbidden


# ---------------------------------------------------------------------------
# Writer Protocol
# ---------------------------------------------------------------------------

class _FakeWriter:
    def append(self, *, execution_account_id, occurred_at_ms, payload):
        return _receipt(execution_account_id=execution_account_id)


class TestExecutionLedgerWriter:
    def test_compatible_fake_is_an_instance(self):
        assert isinstance(_FakeWriter(), ExecutionLedgerWriter)

    def test_objects_without_append_are_not_instances(self):
        class Other:
            def add(self, *, execution_account_id, occurred_at_ms, payload):
                ...

        assert not isinstance(Other(), ExecutionLedgerWriter)
        assert not isinstance(object(), ExecutionLedgerWriter)

    def test_is_a_runtime_checkable_protocol_and_not_instantiable(self):
        assert getattr(ExecutionLedgerWriter, "_is_protocol", False) is True
        with pytest.raises(TypeError):
            ExecutionLedgerWriter()
        isinstance(object(), ExecutionLedgerWriter)  # no TypeError => runtime_checkable

    def test_only_member_is_append(self):
        assert _members(ExecutionLedgerWriter) == ["append"]

    def test_signature_is_exactly_the_adr_011_d2_contract(self):
        sig = inspect.signature(ExecutionLedgerWriter.append)
        assert list(sig.parameters) == ["self", "execution_account_id", "occurred_at_ms", "payload"]
        for name in ("execution_account_id", "occurred_at_ms", "payload"):
            assert sig.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY, name
            assert sig.parameters[name].default is inspect.Parameter.empty, name

    def test_annotations(self):
        hints = typing.get_type_hints(ExecutionLedgerWriter.append)
        assert hints["execution_account_id"] is ExecutionAccountId
        assert hints["occurred_at_ms"] is int
        assert hints["payload"] is ExecutionLedgerEventPayload
        assert hints["return"] is AppendReceipt

    def test_caller_does_not_provide_event_id_sequence_or_commit_time(self):
        params = set(inspect.signature(ExecutionLedgerWriter.append).parameters)
        for forbidden in ("event_id", "event", "sequence", "committed_at_ms", "execution_order_id"):
            assert forbidden not in params, forbidden

    def test_is_synchronous_and_has_no_batch_surface(self):
        assert not inspect.iscoroutinefunction(ExecutionLedgerWriter.append)
        for forbidden in ("append_many", "append_batch", "extend", "bulk_append"):
            assert not hasattr(ExecutionLedgerWriter, forbidden), forbidden

    @pytest.mark.parametrize("verb", [
        "update", "delete", "remove", "replace", "upsert", "mutate", "overwrite", "truncate", "clear", "set",
        "correct", "amend", "merge",
    ])
    def test_append_only_no_mutation_verbs(self, verb):
        assert not hasattr(ExecutionLedgerWriter, verb)
        assert not any(verb in name for name in _members(ExecutionLedgerWriter))

    def test_usage_returns_the_receipt_for_that_account(self):
        receipt = _FakeWriter().append(
            execution_account_id=_OTHER_ACCOUNT, occurred_at_ms=1, payload=_event().payload,
        )
        assert isinstance(receipt, AppendReceipt) and receipt.execution_account_id is _OTHER_ACCOUNT


# ---------------------------------------------------------------------------
# Reader Protocol
# ---------------------------------------------------------------------------

class _FakeReader:
    def read_account_events(self, *, execution_account_id):
        return ()

    def read_order_events(self, *, execution_account_id, execution_order_id):
        return ()

    def read_last_order_event(self, *, execution_account_id, execution_order_id, payload_type):
        return None

    def read_order_ids_with_event_type(self, *, execution_account_id, payload_type):
        return ()


_READER_METHODS = (
    "read_account_events", "read_last_order_event", "read_order_events", "read_order_ids_with_event_type",
)


class TestExecutionLedgerReader:
    def test_compatible_fake_is_an_instance(self):
        assert isinstance(_FakeReader(), ExecutionLedgerReader)

    @pytest.mark.parametrize("missing", _READER_METHODS)
    def test_object_missing_any_method_is_not_an_instance(self, missing):
        class Partial:
            pass

        for name in _READER_METHODS:
            if name != missing:
                setattr(Partial, name, vars(_FakeReader)[name])
        assert not isinstance(Partial(), ExecutionLedgerReader)

    def test_is_a_runtime_checkable_protocol_and_not_instantiable(self):
        assert getattr(ExecutionLedgerReader, "_is_protocol", False) is True
        with pytest.raises(TypeError):
            ExecutionLedgerReader()

    def test_exact_member_set(self):
        assert _members(ExecutionLedgerReader) == sorted(_READER_METHODS)

    @pytest.mark.parametrize("name,params", [
        ("read_account_events", ["self", "execution_account_id"]),
        ("read_order_events", ["self", "execution_account_id", "execution_order_id"]),
        ("read_last_order_event", ["self", "execution_account_id", "execution_order_id", "payload_type"]),
        ("read_order_ids_with_event_type", ["self", "execution_account_id", "payload_type"]),
    ])
    def test_signatures_are_keyword_only_and_exact(self, name, params):
        sig = inspect.signature(getattr(ExecutionLedgerReader, name))
        assert list(sig.parameters) == params
        for p in params[1:]:
            assert sig.parameters[p].kind is inspect.Parameter.KEYWORD_ONLY, (name, p)
            assert sig.parameters[p].default is inspect.Parameter.empty, (name, p)

    def test_return_and_parameter_types(self):
        stored_tuple = tuple[StoredExecutionLedgerEvent, ...]
        h = typing.get_type_hints(ExecutionLedgerReader.read_account_events)
        assert h["execution_account_id"] is ExecutionAccountId and h["return"] == stored_tuple
        h = typing.get_type_hints(ExecutionLedgerReader.read_order_events)
        assert h["execution_order_id"] is ExecutionOrderId and h["return"] == stored_tuple
        h = typing.get_type_hints(ExecutionLedgerReader.read_last_order_event)
        assert h["payload_type"] == type[ExecutionLedgerEventPayload]
        assert h["return"] == (StoredExecutionLedgerEvent | None)
        h = typing.get_type_hints(ExecutionLedgerReader.read_order_ids_with_event_type)
        assert h["payload_type"] == type[ExecutionLedgerEventPayload]
        assert h["return"] == tuple[ExecutionOrderId, ...]

    def test_event_types_are_classes_not_free_strings(self):
        for name in ("read_last_order_event", "read_order_ids_with_event_type"):
            params = inspect.signature(getattr(ExecutionLedgerReader, name)).parameters
            assert "event_type" not in params
            assert typing.get_type_hints(getattr(ExecutionLedgerReader, name))["payload_type"] != str

    # NEUTRALIDAD (ADR-017 D13): ninguna política de Gate en el Reader.
    @pytest.mark.parametrize("fragment", [
        "resolv", "unresolv", "terminal", "block", "halt", "pending", "open_order", "closed", "gate",
        "recover", "status", "state", "need", "outstanding",
    ])
    def test_reader_surface_encodes_no_policy(self, fragment):
        names = _members(ExecutionLedgerReader)
        for name in names:
            assert fragment not in name, (fragment, name)
            params = inspect.signature(getattr(ExecutionLedgerReader, name)).parameters
            assert not any(fragment in p for p in params), (fragment, name)

    def test_reader_does_not_filter_by_a_hardcoded_set_of_event_types(self):
        src = inspect.getsource(_module)
        for event_class in ("OrderAcceptedByExchange", "OrderRejectedByExchange", "OrderObservedClosed",
                            "OrderIdentityReportedDuplicateByExchange", "OrderSubmissionOutcomeUnknown"):
            assert event_class not in src, event_class

    @pytest.mark.parametrize("verb", [
        "append", "update", "delete", "remove", "replace", "upsert", "mutate", "write", "insert", "save",
    ])
    def test_reader_has_no_write_surface(self, verb):
        assert not any(verb in name for name in _members(ExecutionLedgerReader))
        assert not hasattr(ExecutionLedgerReader, verb)

    def test_every_read_is_scoped_by_account(self):
        for name in _READER_METHODS:
            assert "execution_account_id" in inspect.signature(getattr(ExecutionLedgerReader, name)).parameters

    def test_reader_is_synchronous(self):
        for name in _READER_METHODS:
            assert not inspect.iscoroutinefunction(getattr(ExecutionLedgerReader, name))


# ---------------------------------------------------------------------------
# Pureza y exports
# ---------------------------------------------------------------------------

class TestPurityAndExports:
    def _tree(self):
        return ast.parse(inspect.getsource(_module))

    def test_imports_are_exactly_the_domain_contracts(self):
        names = set()
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        assert names == {
            "dataclasses",
            "typing",
            "execution_gateway.execution_identity_contracts",
            "execution_gateway.execution_ledger_event_contracts",
        }

    def test_no_vendor_clock_uuid_environment_network_or_sql_names(self):
        tree = self._tree()
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        names |= {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
        for forbidden in ("psycopg", "Connection", "cursor", "time", "uuid", "uuid4", "environ", "getenv",
                          "socket", "urlopen", "datetime"):
            assert forbidden not in names, forbidden
        src = inspect.getsource(_module)
        for forbidden in ("SELECT ", "INSERT ", "pg_advisory", "synchronous_commit"):
            assert forbidden not in src, forbidden

    def test_module_defines_exactly_the_expected_types(self):
        classes = sorted(
            n for n, o in vars(_module).items() if isinstance(o, type) and o.__module__ == _module.__name__
        )
        assert classes == ["AppendReceipt", "ExecutionLedgerReader", "ExecutionLedgerWriter",
                           "StoredExecutionLedgerEvent"]

    @pytest.mark.parametrize("name", ["AppendReceipt", "StoredExecutionLedgerEvent",
                                      "ExecutionLedgerWriter", "ExecutionLedgerReader"])
    def test_exported_from_package(self, name):
        assert getattr(execution_gateway, name) is getattr(_module, name)
        assert name in execution_gateway.__all__
