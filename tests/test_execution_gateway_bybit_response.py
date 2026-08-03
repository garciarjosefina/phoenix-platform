import os
import pytest
import execution_gateway
from execution_gateway.bybit_response import BybitResponse


# ── helper ─────────────────────────────────────────────────────────────────

def _make_response(**kwargs) -> BybitResponse:
    defaults = dict(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1_700_000_000_000)
    return BybitResponse(**{**defaults, **kwargs})


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_response import BybitResponse as R
        assert R is BybitResponse

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitResponse")
        assert execution_gateway.BybitResponse is BybitResponse

    def test_in_all(self):
        assert "BybitResponse" in execution_gateway.__all__


# ── valid construction ─────────────────────────────────────────────────────

class TestConstruction:
    def test_success_response(self):
        r = _make_response(ret_code=0, ret_msg="OK")
        assert r.ret_code == 0
        assert r.ret_msg == "OK"

    def test_error_response(self):
        r = _make_response(ret_code=10001, ret_msg="error")
        assert r.ret_code == 10001
        assert r.ret_msg == "error"

    def test_empty_ret_msg(self):
        r = _make_response(ret_msg="")
        assert r.ret_msg == ""

    def test_result_none(self):
        r = _make_response(result=None)
        assert r.result is None

    def test_ret_ext_info_none(self):
        r = _make_response(ret_ext_info=None)
        assert r.ret_ext_info is None

    def test_time_ms_zero(self):
        r = _make_response(time_ms=0)
        assert r.time_ms == 0

    def test_positive_ret_code(self):
        r = _make_response(ret_code=10001)
        assert r.ret_code == 10001

    def test_negative_ret_code(self):
        r = _make_response(ret_code=-1)
        assert r.ret_code == -1

    def test_all_fields_stored(self):
        result_data = {"orderId": "abc"}
        ext = {}
        r = BybitResponse(
            ret_code=0, ret_msg="OK",
            result=result_data, ret_ext_info=ext, time_ms=1_700_000_000_000
        )
        assert r.ret_code == 0
        assert r.ret_msg == "OK"
        assert r.result == result_data
        assert r.ret_ext_info == ext
        assert r.time_ms == 1_700_000_000_000


# ── immutability and semantics ─────────────────────────────────────────────

class TestImmutabilityAndSemantics:
    def test_frozen_ret_code(self):
        r = _make_response()
        with pytest.raises((AttributeError, TypeError)):
            r.ret_code = 99

    def test_frozen_ret_msg(self):
        r = _make_response()
        with pytest.raises((AttributeError, TypeError)):
            r.ret_msg = "changed"

    def test_frozen_result(self):
        r = _make_response()
        with pytest.raises((AttributeError, TypeError)):
            r.result = {"new": "data"}

    def test_frozen_time_ms(self):
        r = _make_response()
        with pytest.raises((AttributeError, TypeError)):
            r.time_ms = 0

    def test_equality_by_value(self):
        r1 = _make_response(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1000)
        r2 = _make_response(ret_code=0, ret_msg="OK", result={}, ret_ext_info={}, time_ms=1000)
        assert r1 == r2

    def test_inequality_different_ret_code(self):
        r1 = _make_response(ret_code=0)
        r2 = _make_response(ret_code=1)
        assert r1 != r2

    def test_preserves_ret_msg_exactly(self):
        msg = "  param error  "
        r = _make_response(ret_msg=msg)
        assert r.ret_msg == "  param error  "

    def test_preserves_internal_spaces_in_ret_msg(self):
        msg = "invalid  order  qty"
        r = _make_response(ret_msg=msg)
        assert r.ret_msg == msg

    def test_result_preserved_by_value(self):
        data = {"orderId": "xyz", "qty": "0.001"}
        r = _make_response(result=data)
        assert r.result == data

    def test_ret_ext_info_preserved_by_value(self):
        ext = {"meta": "value"}
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info == ext

    def test_dict_result_frozen_as_mapping_proxy(self):
        d = {"key": "val"}
        r = _make_response(result=d)
        from types import MappingProxyType
        assert isinstance(r.result, MappingProxyType)

    def test_list_result_frozen_as_tuple(self):
        lst = [1, 2, 3]
        r = _make_response(result=lst)
        assert r.result == (1, 2, 3)
        assert isinstance(r.result, tuple)

    def test_ret_ext_info_list_frozen_as_tuple(self):
        lst = ["a", "b"]
        r = _make_response(ret_ext_info=lst)
        assert r.ret_ext_info == ("a", "b")
        assert isinstance(r.ret_ext_info, tuple)


# ── ret_code validation ────────────────────────────────────────────────────

class TestRetCodeValidation:
    def test_rejects_str_ret_code(self):
        with pytest.raises(TypeError):
            _make_response(ret_code="0")

    def test_rejects_float_ret_code(self):
        with pytest.raises(TypeError):
            _make_response(ret_code=0.0)

    def test_rejects_none_ret_code(self):
        with pytest.raises(TypeError):
            _make_response(ret_code=None)

    def test_rejects_bool_true_ret_code(self):
        with pytest.raises(TypeError):
            _make_response(ret_code=True)

    def test_rejects_bool_false_ret_code(self):
        with pytest.raises(TypeError):
            _make_response(ret_code=False)


# ── ret_msg validation ─────────────────────────────────────────────────────

class TestRetMsgValidation:
    def test_rejects_int_ret_msg(self):
        with pytest.raises(TypeError):
            _make_response(ret_msg=0)

    def test_rejects_none_ret_msg(self):
        with pytest.raises(TypeError):
            _make_response(ret_msg=None)

    def test_rejects_bytes_ret_msg(self):
        with pytest.raises(TypeError):
            _make_response(ret_msg=b"OK")


# ── result acceptance ──────────────────────────────────────────────────────

class TestResultAcceptance:
    def test_accepts_none(self):
        r = _make_response(result=None)
        assert r.result is None

    def test_accepts_dict(self):
        d = {"orderId": "abc"}
        r = _make_response(result=d)
        assert r.result == d

    def test_accepts_list(self):
        lst = [{"orderId": "abc"}]
        r = _make_response(result=lst)
        assert r.result == (({"orderId": "abc"}),)

    def test_accepts_str(self):
        r = _make_response(result="raw_string")
        assert r.result == "raw_string"

    def test_accepts_int(self):
        r = _make_response(result=42)
        assert r.result == 42

    def test_accepts_nested_structure(self):
        nested = {"orders": [{"id": "1"}, {"id": "2"}]}
        r = _make_response(result=nested)
        assert r.result["orders"] == ({"id": "1"}, {"id": "2"})


# ── ret_ext_info acceptance ────────────────────────────────────────────────

class TestRetExtInfoAcceptance:
    def test_accepts_none(self):
        r = _make_response(ret_ext_info=None)
        assert r.ret_ext_info is None

    def test_accepts_dict(self):
        ext = {"reqId": "req_001"}
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info == ext

    def test_accepts_list(self):
        ext = [1, 2]
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info == (1, 2)

    def test_accepts_empty_dict(self):
        r = _make_response(ret_ext_info={})
        assert r.ret_ext_info == {}


# ── time_ms validation ─────────────────────────────────────────────────────

class TestTimeMsValidation:
    def test_rejects_str_time_ms(self):
        with pytest.raises(TypeError):
            _make_response(time_ms="1000")

    def test_rejects_float_time_ms(self):
        with pytest.raises(TypeError):
            _make_response(time_ms=1000.0)

    def test_rejects_none_time_ms(self):
        with pytest.raises(TypeError):
            _make_response(time_ms=None)

    def test_rejects_bool_true_time_ms(self):
        with pytest.raises(TypeError):
            _make_response(time_ms=True)

    def test_rejects_bool_false_time_ms(self):
        with pytest.raises(TypeError):
            _make_response(time_ms=False)

    def test_rejects_negative_time_ms(self):
        with pytest.raises(ValueError):
            _make_response(time_ms=-1)

    def test_accepts_zero_time_ms(self):
        r = _make_response(time_ms=0)
        assert r.time_ms == 0

    def test_accepts_large_time_ms(self):
        r = _make_response(time_ms=1_700_000_000_000)
        assert r.time_ms == 1_700_000_000_000


# ── inmutabilidad profunda (Core Hardening Pack A, Parte E) ────────────────

class TestDeepImmutability:
    def test_mutating_original_dict_does_not_affect_stored_result(self):
        original = {"orderId": "abc"}
        r = _make_response(result=original)
        original["orderId"] = "mutated"
        assert r.result["orderId"] == "abc"

    def test_mutating_original_list_does_not_affect_stored_result(self):
        original = [1, 2, 3]
        r = _make_response(result=original)
        original.append(4)
        assert r.result == (1, 2, 3)

    def test_stored_dict_result_cannot_be_mutated(self):
        r = _make_response(result={"a": 1})
        with pytest.raises(TypeError):
            r.result["b"] = 2

    def test_stored_nested_dict_cannot_be_mutated(self):
        r = _make_response(result={"outer": {"inner": 1}})
        with pytest.raises(TypeError):
            r.result["outer"]["inner"] = 2

    def test_stored_tuple_result_cannot_be_appended(self):
        r = _make_response(result=[1, 2])
        with pytest.raises(AttributeError):
            r.result.append(3)

    def test_nested_list_inside_dict_frozen_as_tuple(self):
        r = _make_response(result={"orders": [1, 2, 3]})
        assert isinstance(r.result["orders"], tuple)
        with pytest.raises(AttributeError):
            r.result["orders"].append(4)

    def test_nested_dict_inside_list_frozen_as_mapping_proxy(self):
        from types import MappingProxyType
        r = _make_response(result=[{"id": "1"}, {"id": "2"}])
        assert isinstance(r.result[0], MappingProxyType)
        with pytest.raises(TypeError):
            r.result[0]["id"] = "mutated"

    def test_doubly_nested_structure_fully_frozen(self):
        original = {"orders": [{"id": "1", "tags": ["a", "b"]}]}
        r = _make_response(result=original)
        with pytest.raises(TypeError):
            r.result["orders"][0]["tags"][0] = "z"
        with pytest.raises(AttributeError):
            r.result["orders"][0]["tags"].append("c")

    def test_no_information_lost_after_freezing(self):
        original = {"a": 1, "b": [1, 2, {"c": "d"}], "e": None, "f": "text"}
        r = _make_response(result=original)
        assert r.result["a"] == 1
        assert r.result["b"] == (1, 2, {"c": "d"})
        assert r.result["b"][2]["c"] == "d"
        assert r.result["e"] is None
        assert r.result["f"] == "text"

    def test_equality_preserved_after_freezing(self):
        r1 = _make_response(result={"a": [1, 2]})
        r2 = _make_response(result={"a": [1, 2]})
        assert r1 == r2

    def test_scalars_not_transformed(self):
        r = _make_response(result="raw_string")
        assert r.result == "raw_string"
        assert isinstance(r.result, str)
        r_int = _make_response(result=42)
        assert r_int.result == 42
        assert isinstance(r_int.result, int)

    def test_compatible_with_response_interpreter(self):
        from execution_gateway.bybit_create_order_response_interpreter import (
            BybitCreateOrderResponseInterpreter,
        )
        from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
        r = _make_response(result={"orderId": "x", "orderLinkId": "y"}, ret_code=0)
        result = BybitCreateOrderResponseInterpreter().interpret(response=r)
        assert result == BybitCreateOrderResult(order_id="x", order_link_id="y")

    def test_set_result_frozen_as_frozenset(self):
        r = _make_response(result={1, 2, 3})
        assert isinstance(r.result, frozenset)
        assert r.result == frozenset({1, 2, 3})


# ── no extra behaviour ─────────────────────────────────────────────────────

class TestNoExtraBehaviour:
    def test_no_is_success_method(self):
        r = _make_response()
        assert not hasattr(r, "is_success")

    def test_no_raise_for_error_method(self):
        r = _make_response()
        assert not hasattr(r, "raise_for_error")

    def test_error_code_does_not_raise(self):
        r = _make_response(ret_code=10001, ret_msg="param error")
        assert r.ret_code == 10001

    def test_no_json_knowledge(self):
        import execution_gateway.bybit_response as m
        assert not hasattr(m, "json")
        assert not hasattr(m, "JsonSerializer")

    def test_no_http_knowledge(self):
        import execution_gateway.bybit_response as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "urllib")

    def test_no_sender_knowledge(self):
        import execution_gateway.bybit_response as m
        assert not hasattr(m, "BybitPrivateRequestSender")

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__response_sentinel__"
        try:
            r = _make_response()
            assert r is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.http_request import HttpRequest
        assert GatewayConfig().environment == "demo"
        req = HttpRequest(url="https://example.com", headers={}, body="")
        assert req.body == ""
