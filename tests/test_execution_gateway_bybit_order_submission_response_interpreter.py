import ast
import inspect
from collections.abc import Mapping

import pytest

import execution_gateway
import execution_gateway.bybit_order_submission_response_interpreter as _module
from execution_gateway.bybit_gateway import _ORDER_REJECTION_RET_CODES as _LEGACY_REJECTION_CODES
from execution_gateway.bybit_order_submission_response_interpreter import (
    BybitOrderSubmissionResponseInterpreter,
)
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.order_submission_outcome_contracts import (
    OrderSubmissionOutcome,
    SubmissionAccepted,
    SubmissionIdentityDuplicate,
    SubmissionOutcomeUnknown,
    SubmissionRejected,
)

_LINK = "ord_" + "a" * 32
_REMOTE = "bybit-remote-9f3"
_REJECTION_CODES = (10001, 110003, 110004, 110007)


def _response(*, ret_code=0, ret_msg="OK", result=None, time_ms=1_700_000_000_123):
    if result is None:
        result = {"orderId": _REMOTE, "orderLinkId": _LINK}
    return BybitResponse(
        ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms,
    )


def _interpret(response, link=_LINK):
    return BybitOrderSubmissionResponseInterpreter().interpret(
        response=response, expected_order_link_id=link,
    )


class _Obj:
    pass


# ---------------------------------------------------------------------------
# Aceptación
# ---------------------------------------------------------------------------

class TestAccepted:
    def test_success_returns_submission_accepted(self):
        outcome = _interpret(_response())
        assert type(outcome) is SubmissionAccepted

    def test_exchange_order_id_is_the_remote_order_id_not_the_link_id(self):
        outcome = _interpret(_response())
        assert outcome.exchange_order_id == _REMOTE
        assert outcome.exchange_order_id != _LINK

    def test_server_time_ms_is_the_response_time_literal(self):
        assert _interpret(_response(time_ms=1_700_000_000_123)).server_time_ms == 1_700_000_000_123
        assert _interpret(_response(time_ms=42)).server_time_ms == 42
        assert _interpret(_response(time_ms=0)).server_time_ms == 0

    @pytest.mark.parametrize("remote", [" BYBIT-x ", "AbC-123", "  padded", "trailing  ", "9" * 40])
    def test_exchange_order_id_preserved_literally(self, remote):
        outcome = _interpret(_response(result={"orderId": remote, "orderLinkId": _LINK}))
        assert outcome.exchange_order_id == remote

    def test_ret_msg_of_a_success_response_is_irrelevant(self):
        assert _interpret(_response(ret_msg="")).exchange_order_id == _REMOTE
        assert _interpret(_response(ret_msg="  anything ")).exchange_order_id == _REMOTE

    def test_extra_result_keys_are_ignored(self):
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": _LINK, "extra": 1}))
        assert type(outcome) is SubmissionAccepted

    def test_accepted_carries_exactly_the_fields_of_the_outcome(self):
        outcome = _interpret(_response())
        assert vars(outcome) == {"exchange_order_id": _REMOTE, "server_time_ms": 1_700_000_000_123}

    def test_remote_order_id_equal_to_link_id_is_still_the_remote_value(self):
        outcome = _interpret(_response(result={"orderId": _LINK, "orderLinkId": _LINK}))
        assert outcome.exchange_order_id == _LINK


class TestAcceptedMalformedIsNeverAccepted:
    @pytest.mark.parametrize("result", ["text", 5, 1.5, [], ("orderId", "orderLinkId"), True],
                             ids=["str", "int", "float", "list", "tuple", "bool"])
    def test_result_that_is_not_a_mapping(self, result):
        # `[]` y `()` llegan como tuple (deep-freeze) -- ninguna es Mapping.
        outcome = _interpret(_response(result=result))
        assert outcome == SubmissionOutcomeUnknown(reason="malformed_response")

    def test_result_none_literal(self):
        response = BybitResponse(ret_code=0, ret_msg="OK", result=None, ret_ext_info={}, time_ms=1)
        assert _interpret(response) == SubmissionOutcomeUnknown(reason="malformed_response")

    @pytest.mark.parametrize("result", [
        {}, {"orderId": _REMOTE}, {"orderLinkId": _LINK}, {"order_id": _REMOTE, "order_link_id": _LINK},
    ], ids=["empty", "no-link", "no-order-id", "snake-case"])
    def test_missing_keys(self, result):
        assert _interpret(_response(result=result)) == SubmissionOutcomeUnknown(reason="malformed_response")

    @pytest.mark.parametrize("bad", [None, 1, True, 1.5, ["x"], {}, b"abc", "", "   ", "\t"])
    def test_order_id_invalid(self, bad):
        outcome = _interpret(_response(result={"orderId": bad, "orderLinkId": _LINK}))
        assert outcome == SubmissionOutcomeUnknown(reason="malformed_response")

    @pytest.mark.parametrize("bad", [None, 1, True, 1.5, ["x"], {}, "", "   ", "x" * 37])
    def test_order_link_id_invalid(self, bad):
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": bad}))
        assert outcome == SubmissionOutcomeUnknown(reason="malformed_response")


class TestIdentityMismatch:
    @pytest.mark.parametrize("echoed", [
        "ord_" + "b" * 32, _LINK.upper(), _LINK[:-1], "X", _LINK[1:] + "z",
    ], ids=["other", "upper", "truncated", "short", "shifted"])
    def test_link_id_that_differs_from_the_expected_one(self, echoed):
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": echoed}))
        assert outcome == SubmissionOutcomeUnknown(reason="identity_mismatch")

    @pytest.mark.parametrize("expected,echoed", [
        ("ord_short", " ord_short"), ("ord_short", "ord_short "), (" ord_short", "ord_short"),
        ("ord_short", "ORD_SHORT"),
    ], ids=["echo-lead-pad", "echo-trail-pad", "expected-lead-pad", "case"])
    def test_padding_and_casing_differences_are_mismatches(self, expected, echoed):
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": echoed}), link=expected)
        assert outcome == SubmissionOutcomeUnknown(reason="identity_mismatch")

    def test_mismatch_is_never_accepted(self):
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": "ord_" + "c" * 32}))
        assert not isinstance(outcome, SubmissionAccepted)

    def test_the_expected_link_id_is_compared_literally(self):
        padded = " ord_short "
        outcome = _interpret(_response(result={"orderId": _REMOTE, "orderLinkId": padded}), link=padded)
        assert type(outcome) is SubmissionAccepted


# ---------------------------------------------------------------------------
# Rechazo
# ---------------------------------------------------------------------------

class TestRejected:
    @pytest.mark.parametrize("code", _REJECTION_CODES)
    def test_every_rejection_code_returns_submission_rejected(self, code):
        outcome = _interpret(_response(ret_code=code, ret_msg="bad", result={}))
        assert type(outcome) is SubmissionRejected
        assert outcome.ret_code == code

    @pytest.mark.parametrize("code,msg", [
        (10001, "Request parameter error"), (110003, "  Order price is out of permissible range "),
        (110004, "Insufficient Wallet Balance"), (110007, "ab not enough for new order"),
    ])
    def test_ret_code_ret_msg_and_time_are_literal(self, code, msg):
        outcome = _interpret(_response(ret_code=code, ret_msg=msg, result={}, time_ms=31_337))
        assert (outcome.ret_code, outcome.ret_msg, outcome.server_time_ms) == (code, msg, 31_337)

    @pytest.mark.parametrize("msg", ["  Padded  ", "UPPER", "lower", "MiXeD Case\n", "\tTab"])
    def test_ret_msg_is_not_normalized(self, msg):
        assert _interpret(_response(ret_code=10001, ret_msg=msg, result={})).ret_msg == msg

    def test_rejection_does_not_depend_on_result_content(self):
        for result in ({}, {"orderId": _REMOTE, "orderLinkId": _LINK}, {"x": 1}):
            assert type(_interpret(_response(ret_code=110004, result=result))) is SubmissionRejected

    def test_rejection_is_not_a_duplicate_or_unknown_or_accepted(self):
        outcome = _interpret(_response(ret_code=110003, result={}))
        assert not isinstance(outcome, (SubmissionIdentityDuplicate, SubmissionOutcomeUnknown, SubmissionAccepted))

    def test_the_rejection_set_equals_the_legacy_gateway_set(self):
        assert _module._ORDER_REJECTION_RET_CODES == _LEGACY_REJECTION_CODES == frozenset(_REJECTION_CODES)

    def test_110072_is_never_a_rejection(self):
        assert 110072 not in _module._ORDER_REJECTION_RET_CODES
        assert not isinstance(_interpret(_response(ret_code=110072, result={})), SubmissionRejected)


# ---------------------------------------------------------------------------
# 110072
# ---------------------------------------------------------------------------

class TestIdentityDuplicate:
    def test_110072_returns_identity_duplicate(self):
        outcome = _interpret(_response(ret_code=110072, ret_msg="OrderLinkedID is duplicate", result={}))
        assert type(outcome) is SubmissionIdentityDuplicate

    def test_all_remote_fields_are_literal(self):
        outcome = _interpret(_response(ret_code=110072, ret_msg=" OrderLinkedID  is DUPLICATE ", result={}, time_ms=9_001))
        assert (outcome.ret_code, outcome.ret_msg, outcome.server_time_ms) == (
            110072, " OrderLinkedID  is DUPLICATE ", 9_001,
        )

    def test_it_is_not_a_rejection_acceptance_or_unknown(self):
        outcome = _interpret(_response(ret_code=110072, ret_msg="dup", result={}))
        assert not isinstance(outcome, (SubmissionRejected, SubmissionAccepted, SubmissionOutcomeUnknown))

    def test_a_result_that_looks_like_an_acceptance_does_not_turn_a_duplicate_into_accepted(self):
        outcome = _interpret(_response(ret_code=110072, ret_msg="dup"))
        assert type(outcome) is SubmissionIdentityDuplicate

    @pytest.mark.parametrize("code", [110071, 110073, 110014, 110030, 110072 - 1000, 11072, 1100720])
    def test_neighbouring_codes_are_not_duplicates(self, code):
        assert not isinstance(_interpret(_response(ret_code=code, result={})), SubmissionIdentityDuplicate)


# ---------------------------------------------------------------------------
# Ambigüedad
# ---------------------------------------------------------------------------

class TestAmbiguousBusinessResponse:
    @pytest.mark.parametrize("code", [
        1, -1, 10002, 10003, 10004, 10005, 10006, 10016, 10018, 20001, 110001, 110005, 110006, 110008,
        110014, 110030, 110071, 110073, 130021, 170131, 99999999,
    ])
    def test_every_unclassified_code_is_ambiguous_never_a_rejection(self, code):
        assert _interpret(_response(ret_code=code, ret_msg="msg", result={})) == SubmissionOutcomeUnknown(
            reason="ambiguous_business_response",
        )

    def test_ambiguity_never_becomes_rejected_or_accepted(self):
        outcome = _interpret(_response(ret_code=10006, ret_msg="Too many visits", result={}))
        assert not isinstance(outcome, (SubmissionRejected, SubmissionAccepted, SubmissionIdentityDuplicate))


class TestBlankRetMsgOnClassifiedCodes:
    # Un `ret_msg` vacío/blanco no puede representarse como Rejected/Duplicate
    # sin inventarlo (el outcome lo prohíbe): respuesta recibida pero no
    # interpretable con certeza => `malformed_response` (nunca un ret_msg
    # fabricado, nunca una excepción local).
    @pytest.mark.parametrize("code", [*_REJECTION_CODES, 110072])
    @pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
    def test_blank_ret_msg(self, code, blank):
        assert _interpret(_response(ret_code=code, ret_msg=blank, result={})) == SubmissionOutcomeUnknown(
            reason="malformed_response",
        )

    def test_blank_ret_msg_on_an_unclassified_code_is_still_ambiguous(self):
        assert _interpret(_response(ret_code=10006, ret_msg="", result={})) == SubmissionOutcomeUnknown(
            reason="ambiguous_business_response",
        )


class TestOutcomeFamily:
    @pytest.mark.parametrize("response", [
        lambda: _response(),
        lambda: _response(ret_code=10001, result={}),
        lambda: _response(ret_code=110072, result={}),
        lambda: _response(ret_code=10006, result={}),
    ], ids=["accepted", "rejected", "duplicate", "unknown"])
    def test_every_path_returns_a_family_member_and_never_raises(self, response):
        assert isinstance(_interpret(response()), OrderSubmissionOutcome)


# ---------------------------------------------------------------------------
# Errores de programación
# ---------------------------------------------------------------------------

class TestProgrammingErrorsPropagate:
    @pytest.mark.parametrize("bad", [None, "response", {"ret_code": 0}, _Obj(), 0])
    def test_response_must_be_bybit_response(self, bad):
        with pytest.raises(TypeError):
            BybitOrderSubmissionResponseInterpreter().interpret(response=bad, expected_order_link_id=_LINK)

    @pytest.mark.parametrize("bad", [None, 1, b"x", _Obj()])
    def test_expected_link_id_must_be_str(self, bad):
        with pytest.raises(TypeError):
            BybitOrderSubmissionResponseInterpreter().interpret(response=_response(), expected_order_link_id=bad)

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_expected_link_id_must_not_be_blank(self, bad):
        with pytest.raises(ValueError):
            BybitOrderSubmissionResponseInterpreter().interpret(response=_response(), expected_order_link_id=bad)

    def test_keyword_only_signature(self):
        with pytest.raises(TypeError):
            BybitOrderSubmissionResponseInterpreter().interpret(_response(), _LINK)


# ---------------------------------------------------------------------------
# Datos remotos nunca coaccionados desde el cable
# ---------------------------------------------------------------------------

class TestBybitResponseDoesNotAllowCoercedCodes:
    @pytest.mark.parametrize("bad", [True, False, 0.0, 10001.0, "0", None])
    def test_ret_code_must_be_a_real_int(self, bad):
        with pytest.raises(TypeError):
            BybitResponse(ret_code=bad, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1)

    @pytest.mark.parametrize("bad", [True, 1.0, "1", None, -1])
    def test_time_ms_must_be_a_real_non_negative_int(self, bad):
        with pytest.raises((TypeError, ValueError)):
            BybitResponse(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=bad)


# ---------------------------------------------------------------------------
# Pureza / acoplamiento
# ---------------------------------------------------------------------------

def _imports(module):
    names = set()
    for node in ast.walk(ast.parse(inspect.getsource(module))):
        if isinstance(node, ast.Import):
            names |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module)
    return names


class TestPurityAndCoupling:
    def test_exact_imports(self):
        assert _imports(_module) == {
            "collections.abc",
            "execution_gateway.bybit_create_order_result",
            "execution_gateway.bybit_response",
            "execution_gateway.order_submission_outcome_contracts",
        }

    def test_does_not_import_the_ledger_or_identity_modules(self):
        assert not any("ledger" in name or "identity" in name for name in _imports(_module))

    def test_no_clock_uuid_network_or_environment_names(self):
        names = set()
        for node in ast.walk(ast.parse(inspect.getsource(_module))):
            if isinstance(node, ast.Name):
                names.add(node.id)
            elif isinstance(node, ast.Attribute):
                names.add(node.attr)
        for forbidden in ("time", "uuid", "urlopen", "environ", "getenv", "socket", "datetime",
                          "ExecutionLedgerEvent", "ExecutionOrderId", "OrderAcceptedByExchange",
                          "OrderRejectedByExchange", "OrderIdentityReportedDuplicateByExchange"):
            assert forbidden not in names

    def test_has_no_loop_and_no_exception_handler_other_than_the_result_validation(self):
        tree = ast.parse(inspect.getsource(_module))
        assert not [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
        handlers = [n for n in ast.walk(tree) if isinstance(n, ast.ExceptHandler)]
        assert len(handlers) == 1
        assert ast.unparse(handlers[0].type) == "(TypeError, ValueError)"

    def test_exported_from_package(self):
        assert execution_gateway.BybitOrderSubmissionResponseInterpreter is BybitOrderSubmissionResponseInterpreter
        assert "BybitOrderSubmissionResponseInterpreter" in execution_gateway.__all__

    def test_interpreter_is_stateless(self):
        assert vars(BybitOrderSubmissionResponseInterpreter()) == {}

    @pytest.mark.parametrize("response", [
        lambda: _response(),
        lambda: _response(ret_code=10001, result={}),
        lambda: _response(ret_code=110072, result={}),
        lambda: _response(ret_code=10006, result={}),
        lambda: _response(result={"orderId": _REMOTE}),
    ], ids=["accepted", "rejected", "duplicate", "unclassified", "malformed"])
    def test_interpreting_leaves_no_state_behind(self, response):
        interpreter = BybitOrderSubmissionResponseInterpreter()
        interpreter.interpret(response=response(), expected_order_link_id=_LINK)
        assert vars(interpreter) == {}

    def test_result_mapping_contract_is_the_frozen_proxy(self):
        assert isinstance(_response().result, Mapping)
