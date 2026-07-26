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
        assert r.result is result_data
        assert r.ret_ext_info is ext
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

    def test_result_preserved_by_identity(self):
        data = {"orderId": "xyz", "qty": "0.001"}
        r = _make_response(result=data)
        assert r.result is data

    def test_ret_ext_info_preserved_by_identity(self):
        ext = {"meta": "value"}
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info is ext

    def test_no_list_copy(self):
        lst = [1, 2, 3]
        r = _make_response(result=lst)
        assert r.result is lst

    def test_no_dict_copy(self):
        d = {"key": "val"}
        r = _make_response(result=d)
        assert r.result is d

    def test_no_ret_ext_info_list_copy(self):
        lst = ["a", "b"]
        r = _make_response(ret_ext_info=lst)
        assert r.ret_ext_info is lst


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
        assert r.result is d

    def test_accepts_list(self):
        lst = [{"orderId": "abc"}]
        r = _make_response(result=lst)
        assert r.result is lst

    def test_accepts_str(self):
        r = _make_response(result="raw_string")
        assert r.result == "raw_string"

    def test_accepts_int(self):
        r = _make_response(result=42)
        assert r.result == 42

    def test_accepts_nested_structure(self):
        nested = {"orders": [{"id": "1"}, {"id": "2"}]}
        r = _make_response(result=nested)
        assert r.result is nested


# ── ret_ext_info acceptance ────────────────────────────────────────────────

class TestRetExtInfoAcceptance:
    def test_accepts_none(self):
        r = _make_response(ret_ext_info=None)
        assert r.ret_ext_info is None

    def test_accepts_dict(self):
        ext = {"reqId": "req_001"}
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info is ext

    def test_accepts_list(self):
        ext = [1, 2]
        r = _make_response(ret_ext_info=ext)
        assert r.ret_ext_info is ext

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
