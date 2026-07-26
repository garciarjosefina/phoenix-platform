import pytest

from execution_gateway import BybitApiError
import execution_gateway
import execution_gateway.bybit_api_error as _module


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_api_error import BybitApiError as E
        assert E is BybitApiError

    def test_importable_from_package(self):
        from execution_gateway import BybitApiError as E
        assert E is BybitApiError

    def test_included_in_all(self):
        assert "BybitApiError" in execution_gateway.__all__

    def test_inherits_from_exception(self):
        assert issubclass(BybitApiError, Exception)

    def test_does_not_inherit_from_value_error(self):
        assert not issubclass(BybitApiError, ValueError)

    def test_is_direct_subclass_of_exception(self):
        assert Exception in BybitApiError.__bases__


# ---------------------------------------------------------------------------
# 2. Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_valid_construction(self):
        err = BybitApiError(ret_code=10001, ret_msg="Request parameter error")
        assert err is not None

    def test_arguments_are_keyword_only(self):
        with pytest.raises(TypeError):
            BybitApiError(10001, "some message")

    def test_stores_ret_code(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert err.ret_code == 10001

    def test_stores_ret_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="Request parameter error")
        assert err.ret_msg == "Request parameter error"

    def test_accepts_positive_code(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert err.ret_code == 10001

    def test_accepts_negative_code(self):
        err = BybitApiError(ret_code=-1, ret_msg="msg")
        assert err.ret_code == -1

    def test_accepts_zero_code(self):
        err = BybitApiError(ret_code=0, ret_msg="msg")
        assert err.ret_code == 0

    def test_accepts_empty_ret_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="")
        assert err.ret_msg == ""

    def test_accepts_whitespace_ret_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="   ")
        assert err.ret_msg == "   "

    def test_preserves_leading_trailing_spaces(self):
        err = BybitApiError(ret_code=10001, ret_msg="  padded  ")
        assert err.ret_msg == "  padded  "

    def test_preserves_ret_code_exactly(self):
        err = BybitApiError(ret_code=99999, ret_msg="msg")
        assert err.ret_code == 99999
        assert err.ret_code is not True

    def test_preserves_ret_msg_exactly(self):
        msg = "Error: invalid\tsymbol\n"
        err = BybitApiError(ret_code=10001, ret_msg=msg)
        assert err.ret_msg is msg


# ---------------------------------------------------------------------------
# 3. Validación de ret_code
# ---------------------------------------------------------------------------

class TestRetCodeValidation:
    def test_rejects_string(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code="10001", ret_msg="msg")

    def test_rejects_float(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code=10001.0, ret_msg="msg")

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code=None, ret_msg="msg")

    def test_rejects_list(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code=[10001], ret_msg="msg")

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code={"code": 10001}, ret_msg="msg")

    def test_rejects_true(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code=True, ret_msg="msg")

    def test_rejects_false(self):
        with pytest.raises(TypeError, match="ret_code must be int"):
            BybitApiError(ret_code=False, ret_msg="msg")

    def test_does_not_convert_via_int(self):
        with pytest.raises(TypeError):
            BybitApiError(ret_code="10001", ret_msg="msg")


# ---------------------------------------------------------------------------
# 4. Validación de ret_msg
# ---------------------------------------------------------------------------

class TestRetMsgValidation:
    def test_rejects_none(self):
        with pytest.raises(TypeError, match="ret_msg must be str"):
            BybitApiError(ret_code=10001, ret_msg=None)

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="ret_msg must be str"):
            BybitApiError(ret_code=10001, ret_msg=10001)

    def test_rejects_bytes(self):
        with pytest.raises(TypeError, match="ret_msg must be str"):
            BybitApiError(ret_code=10001, ret_msg=b"msg")

    def test_rejects_list(self):
        with pytest.raises(TypeError, match="ret_msg must be str"):
            BybitApiError(ret_code=10001, ret_msg=["msg"])

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="ret_msg must be str"):
            BybitApiError(ret_code=10001, ret_msg={"msg": "x"})

    def test_does_not_convert_via_str(self):
        with pytest.raises(TypeError):
            BybitApiError(ret_code=10001, ret_msg=12345)


# ---------------------------------------------------------------------------
# 5. Mensaje
# ---------------------------------------------------------------------------

class TestMessage:
    def test_str_format(self):
        err = BybitApiError(ret_code=10001, ret_msg="Request parameter error")
        assert str(err) == "Bybit API error 10001: Request parameter error"

    def test_str_format_negative_code(self):
        err = BybitApiError(ret_code=-1, ret_msg="Unknown")
        assert str(err) == "Bybit API error -1: Unknown"

    def test_str_format_empty_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="")
        assert str(err) == "Bybit API error 10001: "

    def test_str_format_whitespace_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="   ")
        assert str(err) == "Bybit API error 10001:    "

    def test_str_format_zero_code(self):
        err = BybitApiError(ret_code=0, ret_msg="OK")
        assert str(err) == "Bybit API error 0: OK"

    def test_args_contains_only_message(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert len(err.args) == 1
        assert err.args[0] == "Bybit API error 10001: msg"

    def test_args_contains_no_extra_fields(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert len(err.args) == 1


# ---------------------------------------------------------------------------
# 6. Excepción real
# ---------------------------------------------------------------------------

class TestAsException:
    def test_can_be_raised(self):
        with pytest.raises(BybitApiError):
            raise BybitApiError(ret_code=10001, ret_msg="error")

    def test_caught_as_bybit_api_error(self):
        try:
            raise BybitApiError(ret_code=10001, ret_msg="caught")
        except BybitApiError as e:
            assert e.ret_code == 10001
            assert e.ret_msg == "caught"

    def test_caught_as_exception(self):
        try:
            raise BybitApiError(ret_code=10001, ret_msg="caught")
        except Exception as e:
            assert isinstance(e, BybitApiError)

    def test_not_caught_as_value_error(self):
        with pytest.raises(BybitApiError):
            try:
                raise BybitApiError(ret_code=10001, ret_msg="not value error")
            except ValueError:
                pytest.fail("BybitApiError must not be caught as ValueError")

    def test_attributes_preserved_after_catch(self):
        try:
            raise BybitApiError(ret_code=99, ret_msg="preserved")
        except BybitApiError as e:
            assert e.ret_code == 99
            assert e.ret_msg == "preserved"
            assert str(e) == "Bybit API error 99: preserved"


# ---------------------------------------------------------------------------
# 7. Superficie mínima
# ---------------------------------------------------------------------------

class TestMinimalSurface:
    def test_public_attributes_are_ret_code_and_ret_msg(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        public = {k for k in vars(err) if not k.startswith("_")}
        assert public == {"ret_code", "ret_msg"}

    def test_no_retryable_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "retryable")

    def test_no_temporary_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "temporary")

    def test_no_category_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "category")

    def test_no_endpoint_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "endpoint")

    def test_no_response_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "response")

    def test_no_request_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "request")

    def test_no_payload_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "payload")

    def test_no_status_code_attribute(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        assert not hasattr(err, "status_code")

    def test_no_extra_public_methods(self):
        err = BybitApiError(ret_code=10001, ret_msg="msg")
        inherited = set(dir(Exception()))
        own_public = {
            n for n in dir(err)
            if not n.startswith("_") and n not in inherited
        }
        assert own_public == {"ret_code", "ret_msg"}


# ---------------------------------------------------------------------------
# 8. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_bybit_response(self):
        assert "BybitResponse" not in vars(_module)

    def test_does_not_import_bybit_demo_client(self):
        assert "BybitDemoClient" not in vars(_module)

    def test_does_not_import_bybit_create_order_operation(self):
        assert "BybitCreateOrderOperation" not in vars(_module)

    def test_does_not_import_interpreter(self):
        assert "BybitCreateOrderResponseInterpreter" not in vars(_module)

    def test_does_not_import_endpoints(self):
        assert "BYBIT_CREATE_ORDER_ENDPOINT" not in vars(_module)
        assert "BybitEndpoint" not in vars(_module)

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_whole_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
