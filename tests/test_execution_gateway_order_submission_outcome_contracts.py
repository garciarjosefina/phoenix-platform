import ast
import dataclasses
import inspect
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.order_submission_outcome_contracts as _module
from execution_gateway import execution_ledger_event_contracts as _ledger
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import (
    ExecutionLedgerEventPayload,
    LocalFact,
    ObservedFact,
    OrderAcceptedByExchange,
    OrderIdentityReportedDuplicateByExchange,
    OrderRejectedByExchange,
    OrderSubmissionOutcomeUnknown,
    RemoteFact,
)
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionAccepted,
    SubmissionIdentityDuplicate,
    SubmissionOutcomeUnknown,
    SubmissionRejected,
)

_ORDER_ID = ExecutionOrderId(value="ord_" + "0123456789abcdef" * 2)
_CONCRETE = (
    SubmissionAccepted, SubmissionRejected, SubmissionIdentityDuplicate, SubmissionOutcomeUnknown,
)
_REASONS = (
    "transport_failure", "malformed_response", "ambiguous_business_response", "identity_mismatch",
)


def _accepted(**overrides):
    kw = dict(exchange_order_id="BYBIT-1", server_time_ms=1000)
    kw.update(overrides)
    return SubmissionAccepted(**kw)


def _rejected(**overrides):
    kw = dict(ret_code=10001, ret_msg="bad order", server_time_ms=1000)
    kw.update(overrides)
    return SubmissionRejected(**kw)


def _duplicate(**overrides):
    kw = dict(ret_code=110072, ret_msg="OrderLinkedID is duplicate", server_time_ms=1000)
    kw.update(overrides)
    return SubmissionIdentityDuplicate(**kw)


def _unknown(**overrides):
    kw = dict(reason="transport_failure")
    kw.update(overrides)
    return SubmissionOutcomeUnknown(**kw)


class _Obj:
    pass


# ---------------------------------------------------------------------------
# Familia nominal: raíz + cuatro concretos, sin herencia cruzada
# ---------------------------------------------------------------------------

class TestFamily:
    @pytest.mark.parametrize("builder", [_accepted, _rejected, _duplicate, _unknown])
    def test_every_concrete_outcome_is_a_family_member(self, builder):
        assert isinstance(builder(), OrderSubmissionOutcome)

    def test_exactly_four_concrete_subtypes_exist_in_the_module(self):
        concrete = {
            name for name, obj in vars(_module).items()
            if isinstance(obj, type) and issubclass(obj, OrderSubmissionOutcome)
            and obj is not OrderSubmissionOutcome
        }
        assert concrete == {
            "SubmissionAccepted", "SubmissionRejected",
            "SubmissionIdentityDuplicate", "SubmissionOutcomeUnknown",
        }

    def test_no_concrete_type_inherits_from_another_concrete_type(self):
        for a in _CONCRETE:
            for b in _CONCRETE:
                if a is not b:
                    assert not issubclass(a, b), (a.__name__, b.__name__)

    def test_duplicate_is_not_a_rejection(self):
        assert not issubclass(SubmissionIdentityDuplicate, SubmissionRejected)
        assert not isinstance(_duplicate(), SubmissionRejected)
        assert not isinstance(_rejected(), SubmissionIdentityDuplicate)

    def test_unknown_is_not_a_rejection(self):
        assert not isinstance(_unknown(), SubmissionRejected)
        assert not isinstance(_rejected(), SubmissionOutcomeUnknown)

    def test_direct_parents_are_exactly_the_family_root(self):
        for cls in _CONCRETE:
            assert cls.__mro__[1] is OrderSubmissionOutcome

    @pytest.mark.parametrize("builder", [_accepted, _rejected, _duplicate, _unknown])
    def test_is_frozen(self, builder):
        ev = builder()
        name = next(iter(dataclasses.fields(ev))).name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(ev, name, getattr(ev, name))

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_concrete_types_are_frozen_dataclasses(self, cls):
        assert dataclasses.is_dataclass(cls)
        assert cls.__dataclass_params__.frozen

    def test_outcomes_do_not_carry_ledger_authority_markers(self):
        # LocalFact/RemoteFact/ObservedFact pertenecen al modelo de eventos
        # del Ledger, no a esta familia (ADR-016 D2).
        for builder in (_accepted, _rejected, _duplicate, _unknown):
            ev = builder()
            assert not isinstance(ev, (LocalFact, RemoteFact, ObservedFact))
            assert not isinstance(ev, ExecutionLedgerEventPayload)


# ---------------------------------------------------------------------------
# SubmissionAccepted
# ---------------------------------------------------------------------------

class TestSubmissionAccepted:
    def test_constructs_validly(self):
        ev = _accepted()
        assert ev.exchange_order_id == "BYBIT-1"
        assert ev.server_time_ms == 1000

    def test_preserves_every_field_with_non_default_values(self):
        ev = SubmissionAccepted(exchange_order_id="bybit-xOrder-77", server_time_ms=4242)
        assert ev.exchange_order_id == "bybit-xOrder-77"
        assert ev.server_time_ms == 4242

    def test_exchange_order_id_with_padding_preserved_literal(self):
        assert _accepted(exchange_order_id=" BYBIT-XORDER-77 ").exchange_order_id == " BYBIT-XORDER-77 "

    def test_exchange_order_id_case_preserved_literal(self):
        assert _accepted(exchange_order_id="abcDEF-9").exchange_order_id == "abcDEF-9"

    def test_server_time_ms_zero_is_valid(self):
        assert _accepted(server_time_ms=0).server_time_ms == 0

    def test_server_time_ms_is_not_silently_reconstructed(self):
        assert _accepted(server_time_ms=4242).server_time_ms == 4242
        assert _accepted(server_time_ms=7).server_time_ms == 7

    @pytest.mark.parametrize("bad", [None, True, 1, 1.5, Decimal("1"), [], {}, b"x", _Obj()])
    def test_exchange_order_id_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _accepted(exchange_order_id=bad)

    @pytest.mark.parametrize("bad", ["", "   ", "\t\n"])
    def test_exchange_order_id_rejects_empty_or_whitespace_only(self, bad):
        with pytest.raises(ValueError):
            _accepted(exchange_order_id=bad)

    @pytest.mark.parametrize("bad", [None, "1000", 1.5, Decimal("1"), [], {}, b"x", _Obj()])
    def test_server_time_ms_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _accepted(server_time_ms=bad)

    @pytest.mark.parametrize("bad", [True, False])
    def test_server_time_ms_rejects_bool(self, bad):
        with pytest.raises(TypeError):
            _accepted(server_time_ms=bad)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError):
            _accepted(server_time_ms=-1)


# ---------------------------------------------------------------------------
# SubmissionRejected
# ---------------------------------------------------------------------------

class TestSubmissionRejected:
    def test_constructs_validly(self):
        ev = _rejected()
        assert (ev.ret_code, ev.ret_msg, ev.server_time_ms) == (10001, "bad order", 1000)

    def test_preserves_every_field_with_non_default_values(self):
        ev = SubmissionRejected(ret_code=110004, ret_msg="Insufficient Balance", server_time_ms=4242)
        assert ev.ret_code == 110004
        assert ev.ret_msg == "Insufficient Balance"
        assert ev.server_time_ms == 4242

    def test_ret_msg_preserved_verbatim_with_padding_and_casing(self):
        assert _rejected(ret_msg="  Order Value BELOW Min  ").ret_msg == "  Order Value BELOW Min  "

    # 110072 -- guarda causal (ADR-013 D3)
    def test_rejects_ret_code_110072(self):
        with pytest.raises(ValueError):
            _rejected(ret_code=110072)

    @pytest.mark.parametrize("code", [10001, 110003, 110004, 110007, 110071, 110073, 0, -1])
    def test_accepts_other_int_ret_codes(self, code):
        assert _rejected(ret_code=code).ret_code == code

    @pytest.mark.parametrize("bad", [True, False])
    def test_ret_code_rejects_bool(self, bad):
        with pytest.raises(TypeError):
            _rejected(ret_code=bad)

    @pytest.mark.parametrize("bad", [None, "10001", 10001.0, Decimal("10001"), [], {}, b"1", _Obj()])
    def test_ret_code_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _rejected(ret_code=bad)

    @pytest.mark.parametrize("bad", [None, 1, 1.5, True, Decimal("1"), [], {}, b"x", _Obj()])
    def test_ret_msg_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _rejected(ret_msg=bad)

    @pytest.mark.parametrize("bad", ["", "   ", "\t"])
    def test_ret_msg_rejects_empty_or_whitespace_only(self, bad):
        with pytest.raises(ValueError):
            _rejected(ret_msg=bad)

    @pytest.mark.parametrize("bad", [None, "1", 1.5, Decimal("1"), [], {}, b"x", _Obj()])
    def test_server_time_ms_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _rejected(server_time_ms=bad)

    @pytest.mark.parametrize("bad", [True, False])
    def test_server_time_ms_rejects_bool(self, bad):
        with pytest.raises(TypeError):
            _rejected(server_time_ms=bad)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError):
            _rejected(server_time_ms=-1)

    def test_no_exchange_order_id(self):
        assert "exchange_order_id" not in {f.name for f in dataclasses.fields(SubmissionRejected)}


# ---------------------------------------------------------------------------
# SubmissionIdentityDuplicate
# ---------------------------------------------------------------------------

class TestSubmissionIdentityDuplicate:
    def test_constructs_validly(self):
        ev = _duplicate()
        assert (ev.ret_code, ev.ret_msg, ev.server_time_ms) == (
            110072, "OrderLinkedID is duplicate", 1000,
        )

    def test_preserves_every_field_with_non_default_values(self):
        ev = SubmissionIdentityDuplicate(
            ret_code=110072, ret_msg=" duplicate  LINK id ", server_time_ms=4242,
        )
        assert ev.ret_code == 110072
        assert ev.ret_msg == " duplicate  LINK id "
        assert ev.server_time_ms == 4242

    @pytest.mark.parametrize("code", [0, 10001, 110003, 110004, 110007, 110071, 110073, 110014, 110030, -1, 1])
    def test_rejects_any_other_int_ret_code(self, code):
        with pytest.raises(ValueError):
            _duplicate(ret_code=code)

    @pytest.mark.parametrize("bad", [True, False])
    def test_ret_code_rejects_bool(self, bad):
        with pytest.raises(TypeError):
            _duplicate(ret_code=bad)

    @pytest.mark.parametrize("bad", [None, "110072", 110072.0, Decimal("110072"), [], {}, b"110072", _Obj()])
    def test_ret_code_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _duplicate(ret_code=bad)

    @pytest.mark.parametrize("bad", [None, 1, 1.5, True, Decimal("1"), [], {}, b"x", _Obj()])
    def test_ret_msg_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _duplicate(ret_msg=bad)

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_ret_msg_rejects_empty_or_whitespace_only(self, bad):
        with pytest.raises(ValueError):
            _duplicate(ret_msg=bad)

    def test_ret_msg_not_required_to_be_the_literal_remote_string(self):
        assert _duplicate(ret_msg="anything non-empty").ret_msg == "anything non-empty"

    @pytest.mark.parametrize("bad", [True, False])
    def test_server_time_ms_rejects_bool(self, bad):
        with pytest.raises(TypeError):
            _duplicate(server_time_ms=bad)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError):
            _duplicate(server_time_ms=-1)

    @pytest.mark.parametrize("bad", [None, "1", 1.5, Decimal("1"), [], {}, b"x", _Obj()])
    def test_server_time_ms_rejects_non_int(self, bad):
        with pytest.raises(TypeError):
            _duplicate(server_time_ms=bad)

    def test_no_exchange_order_id_because_the_remote_never_returns_one(self):
        assert "exchange_order_id" not in {f.name for f in dataclasses.fields(SubmissionIdentityDuplicate)}


# ---------------------------------------------------------------------------
# SubmissionOutcomeUnknown
# ---------------------------------------------------------------------------

class TestSubmissionOutcomeUnknown:
    @pytest.mark.parametrize("reason", _REASONS)
    def test_every_closed_set_reason_is_valid_and_preserved(self, reason):
        assert _unknown(reason=reason).reason == reason

    @pytest.mark.parametrize("bad", [
        "Transport_Failure", "TRANSPORT_FAILURE", " transport_failure", "transport_failure ",
        "unknown", "failure", "timeout", "retry", "", "   ", "transport failure",
    ])
    def test_rejects_every_reason_outside_the_exact_closed_set(self, bad):
        with pytest.raises(ValueError):
            _unknown(reason=bad)

    @pytest.mark.parametrize("bad", [None, 1, True, 1.5, Decimal("1"), [], {}, b"transport_failure", _Obj()])
    def test_reason_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _unknown(reason=bad)

    def test_reason_has_no_default(self):
        with pytest.raises(TypeError):
            SubmissionOutcomeUnknown()

    def test_reason_field_has_no_default_value(self):
        field = dataclasses.fields(SubmissionOutcomeUnknown)[0]
        assert field.default is dataclasses.MISSING
        assert field.default_factory is dataclasses.MISSING

    def test_carries_no_remote_time(self):
        assert "server_time_ms" not in {f.name for f in dataclasses.fields(SubmissionOutcomeUnknown)}

    def test_reason_set_is_exactly_the_four_accepted_categories(self):
        assert _module._VALID_UNKNOWN_REASONS == set(_REASONS)


# ---------------------------------------------------------------------------
# Conjunto exacto de campos y superficie pública -- ADR-016 D2: NINGÚN
# outcome lleva execution_order_id
# ---------------------------------------------------------------------------

_EXPECTED_FIELDS = {
    SubmissionAccepted: {"exchange_order_id", "server_time_ms"},
    SubmissionRejected: {"ret_code", "ret_msg", "server_time_ms"},
    SubmissionIdentityDuplicate: {"ret_code", "ret_msg", "server_time_ms"},
    SubmissionOutcomeUnknown: {"reason"},
}
_BUILDERS = {
    SubmissionAccepted: _accepted,
    SubmissionRejected: _rejected,
    SubmissionIdentityDuplicate: _duplicate,
    SubmissionOutcomeUnknown: _unknown,
}


class TestExactFieldSetsAndPublicSurface:
    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_exact_field_set(self, cls):
        assert {f.name for f in dataclasses.fields(cls)} == _EXPECTED_FIELDS[cls]

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_no_field_has_a_default(self, cls):
        for f in dataclasses.fields(cls):
            assert f.default is dataclasses.MISSING, (cls.__name__, f.name)
            assert f.default_factory is dataclasses.MISSING, (cls.__name__, f.name)

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_public_non_callable_attributes_equal_exactly_the_declared_fields(self, cls):
        # `dir()` incluye propiedades (no almacenadas en `__dict__`) -- una
        # `@property` nueva, p. ej. `execution_order_id`, rompe la igualdad.
        ev = _BUILDERS[cls]()
        actual = {n for n in dir(ev) if not n.startswith("_") and not callable(getattr(ev, n))}
        assert actual == {f.name for f in dataclasses.fields(cls)}

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_execution_order_id_and_identity_or_authority_attributes_are_absent(self, cls):
        ev = _BUILDERS[cls]()
        for forbidden in (
            "execution_order_id", "order_id", "bot_id", "execution_bot_id", "account_id",
            "execution_account_id", "authority", "should_retry", "sequence", "event_id",
            "occurred_at_ms", "committed_at_ms", "raw_response", "headers", "credentials",
        ):
            assert not hasattr(ev, forbidden), forbidden

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_constructor_rejects_execution_order_id_keyword(self, cls):
        kwargs = {f.name: getattr(_BUILDERS[cls](), f.name) for f in dataclasses.fields(cls)}
        with pytest.raises(TypeError):
            cls(execution_order_id=_ORDER_ID, **kwargs)

    @pytest.mark.parametrize("cls", _CONCRETE)
    def test_no_terminality_or_resolution_methods(self, cls):
        for forbidden in ("resolve", "close", "mutate", "correct", "replace", "terminal", "is_terminal"):
            assert not hasattr(cls, forbidden)


# ---------------------------------------------------------------------------
# Isomorfismo con los eventos del Ledger (ADR-016 D2): para cada par,
# campos(evento) == campos(outcome) + {execution_order_id}, mismos tipos y
# mismas validaciones -- sin acoplar producción entre ambos módulos.
# ---------------------------------------------------------------------------

_PAIRS = [
    (SubmissionAccepted, OrderAcceptedByExchange),
    (SubmissionRejected, OrderRejectedByExchange),
    (SubmissionIdentityDuplicate, OrderIdentityReportedDuplicateByExchange),
    (SubmissionOutcomeUnknown, OrderSubmissionOutcomeUnknown),
]


class TestLedgerIsomorphism:
    @pytest.mark.parametrize("outcome_cls,event_cls", _PAIRS, ids=[p[0].__name__ for p in _PAIRS])
    def test_event_fields_equal_outcome_fields_plus_execution_order_id(self, outcome_cls, event_cls):
        outcome_names = {f.name for f in dataclasses.fields(outcome_cls)}
        event_names = {f.name for f in dataclasses.fields(event_cls)}
        assert event_names == outcome_names | {"execution_order_id"}
        assert "execution_order_id" not in outcome_names

    @pytest.mark.parametrize("outcome_cls,event_cls", _PAIRS, ids=[p[0].__name__ for p in _PAIRS])
    def test_shared_fields_have_identical_types_and_requiredness(self, outcome_cls, event_cls):
        event_fields = {f.name: f for f in dataclasses.fields(event_cls)}
        for f in dataclasses.fields(outcome_cls):
            e = event_fields[f.name]
            assert f.type == e.type, (outcome_cls.__name__, f.name)
            assert (f.default is dataclasses.MISSING) == (e.default is dataclasses.MISSING)

    def test_unknown_reason_sets_are_exactly_equal_across_modules(self):
        assert _module._VALID_UNKNOWN_REASONS == _ledger._VALID_OUTCOME_UNKNOWN_REASONS

    @pytest.mark.parametrize("outcome_cls,event_cls,table", [
        (SubmissionAccepted, OrderAcceptedByExchange, [
            dict(exchange_order_id="B", server_time_ms=1), dict(exchange_order_id=" B ", server_time_ms=0),
            dict(exchange_order_id="", server_time_ms=1), dict(exchange_order_id="  ", server_time_ms=1),
            dict(exchange_order_id=None, server_time_ms=1), dict(exchange_order_id=1, server_time_ms=1),
            dict(exchange_order_id="B", server_time_ms=-1), dict(exchange_order_id="B", server_time_ms=True),
            dict(exchange_order_id="B", server_time_ms=1.0), dict(exchange_order_id="B", server_time_ms=None),
            dict(exchange_order_id="B", server_time_ms="1"),
        ]),
        (SubmissionRejected, OrderRejectedByExchange, [
            dict(ret_code=10001, ret_msg="m", server_time_ms=1), dict(ret_code=110072, ret_msg="m", server_time_ms=1),
            dict(ret_code=True, ret_msg="m", server_time_ms=1), dict(ret_code=10001.0, ret_msg="m", server_time_ms=1),
            dict(ret_code="10001", ret_msg="m", server_time_ms=1), dict(ret_code=None, ret_msg="m", server_time_ms=1),
            dict(ret_code=-1, ret_msg="m", server_time_ms=1), dict(ret_code=0, ret_msg="m", server_time_ms=1),
            dict(ret_code=10001, ret_msg="", server_time_ms=1), dict(ret_code=10001, ret_msg="  ", server_time_ms=1),
            dict(ret_code=10001, ret_msg=None, server_time_ms=1), dict(ret_code=10001, ret_msg=" m ", server_time_ms=1),
            dict(ret_code=10001, ret_msg="m", server_time_ms=-1), dict(ret_code=10001, ret_msg="m", server_time_ms=True),
        ]),
        (SubmissionIdentityDuplicate, OrderIdentityReportedDuplicateByExchange, [
            dict(ret_code=110072, ret_msg="m", server_time_ms=1), dict(ret_code=110071, ret_msg="m", server_time_ms=1),
            dict(ret_code=110073, ret_msg="m", server_time_ms=1), dict(ret_code=0, ret_msg="m", server_time_ms=1),
            dict(ret_code=10001, ret_msg="m", server_time_ms=1), dict(ret_code=True, ret_msg="m", server_time_ms=1),
            dict(ret_code=110072.0, ret_msg="m", server_time_ms=1), dict(ret_code="110072", ret_msg="m", server_time_ms=1),
            dict(ret_code=110072, ret_msg="", server_time_ms=1), dict(ret_code=110072, ret_msg="  ", server_time_ms=1),
            dict(ret_code=110072, ret_msg=None, server_time_ms=1), dict(ret_code=110072, ret_msg="m", server_time_ms=-1),
            dict(ret_code=110072, ret_msg="m", server_time_ms=False),
        ]),
        (SubmissionOutcomeUnknown, OrderSubmissionOutcomeUnknown, [
            dict(reason="transport_failure"), dict(reason="malformed_response"),
            dict(reason="ambiguous_business_response"), dict(reason="identity_mismatch"),
            dict(reason="Transport_Failure"), dict(reason=" transport_failure"), dict(reason="unknown"),
            dict(reason=""), dict(reason="  "), dict(reason=None), dict(reason=1), dict(reason=True),
        ]),
    ], ids=[p[0].__name__ for p in _PAIRS])
    def test_construction_outcome_matches_ledger_event_for_every_case(self, outcome_cls, event_cls, table):
        def result(make):
            try:
                make()
            except Exception as error:  # noqa: BLE001 -- comparación de tipo de excepción
                return type(error)
            return "OK"

        for kwargs in table:
            assert result(lambda: outcome_cls(**kwargs)) == result(
                lambda: event_cls(execution_order_id=_ORDER_ID, **kwargs)
            ), kwargs

    @pytest.mark.parametrize("outcome_cls,event_cls", _PAIRS, ids=[p[0].__name__ for p in _PAIRS])
    def test_event_can_be_built_mechanically_from_outcome_plus_identity(self, outcome_cls, event_cls):
        outcome = _BUILDERS[outcome_cls]()
        kwargs = {f.name: getattr(outcome, f.name) for f in dataclasses.fields(outcome)}
        event = event_cls(execution_order_id=_ORDER_ID, **kwargs)
        for name, value in kwargs.items():
            assert getattr(event, name) is value or getattr(event, name) == value
        assert event.execution_order_id is _ORDER_ID


# ---------------------------------------------------------------------------
# Exports a nivel de paquete
# ---------------------------------------------------------------------------

class TestPackageExports:
    @pytest.mark.parametrize("name", [
        "OrderSubmissionOutcome", "SubmissionAccepted", "SubmissionRejected",
        "SubmissionIdentityDuplicate", "SubmissionOutcomeUnknown",
    ])
    def test_outcome_types_importable_from_package_and_in_all(self, name):
        assert getattr(execution_gateway, name) is getattr(_module, name)
        assert name in execution_gateway.__all__


# ---------------------------------------------------------------------------
# Pureza domain-only
# ---------------------------------------------------------------------------

class TestPurity:
    def _imports(self):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(_module))):
            if isinstance(node, ast.Import):
                names |= {a.name for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add(node.module)
        return names

    def test_imports_only_dataclasses(self):
        assert self._imports() == {"dataclasses"}

    def test_does_not_import_the_ledger_module(self):
        assert not any("ledger" in name for name in self._imports())

    def test_no_clock_uuid_network_or_environment_names(self):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(_module))):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("time", "uuid", "urlopen", "environ", "getenv", "socket", "datetime"):
            assert forbidden not in names

    def test_no_mutable_module_level_state(self):
        for name, value in vars(_module).items():
            if name.startswith("_") and not name.startswith("__") and not callable(value):
                assert not isinstance(value, (list, dict)), name
