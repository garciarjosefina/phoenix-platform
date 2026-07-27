import pytest

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_create_order_response_interpreter import (
    BybitCreateOrderResponseInterpreter,
)
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_response import BybitResponse
import execution_gateway
import execution_gateway.bybit_create_order_response_interpreter as _module


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MISSING = object()


def _make_response(
    ret_code: int = 0,
    ret_msg: str = "OK",
    result: object = _MISSING,
) -> BybitResponse:
    if result is _MISSING:
        result = {"orderId": "123456789", "orderLinkId": "test-link-id"}
    return BybitResponse(
        ret_code=ret_code,
        ret_msg=ret_msg,
        result=result,
        ret_ext_info={},
        time_ms=1000,
    )


def _interp() -> BybitCreateOrderResponseInterpreter:
    return BybitCreateOrderResponseInterpreter()


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_create_order_response_interpreter import (
            BybitCreateOrderResponseInterpreter as C,
        )
        assert C is BybitCreateOrderResponseInterpreter

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitCreateOrderResponseInterpreter")
        assert execution_gateway.BybitCreateOrderResponseInterpreter is BybitCreateOrderResponseInterpreter

    def test_in_all(self):
        assert "BybitCreateOrderResponseInterpreter" in execution_gateway.__all__

    def test_construction_without_args(self):
        interp = BybitCreateOrderResponseInterpreter()
        assert interp is not None

    def test_only_interpret_public_method(self):
        interp = _interp()
        public = {n for n in dir(interp) if not n.startswith("_")}
        assert public == {"interpret"}

    def test_interpreter_uses_bybit_api_error(self):
        assert "BybitApiError" in vars(_module)


# ---------------------------------------------------------------------------
# 2. Entrada
# ---------------------------------------------------------------------------

class TestInput:
    def test_response_is_keyword_only(self):
        with pytest.raises(TypeError):
            _interp().interpret(_make_response())

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            _interp().interpret(response=None)

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            _interp().interpret(response={"ret_code": 0})

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            _interp().interpret(response=0)

    def test_accepts_bybit_response(self):
        result = _interp().interpret(response=_make_response())
        assert isinstance(result, BybitCreateOrderResult)


# ---------------------------------------------------------------------------
# 3. Respuesta exitosa
# ---------------------------------------------------------------------------

class TestSuccessfulResponse:
    def test_ret_code_zero_accepted(self):
        result = _interp().interpret(response=_make_response(ret_code=0))
        assert isinstance(result, BybitCreateOrderResult)

    def test_extracts_order_id(self):
        r = _make_response(result={"orderId": "987654321", "orderLinkId": "link-1"})
        result = _interp().interpret(response=r)
        assert result.order_id == "987654321"

    def test_extracts_order_link_id(self):
        r = _make_response(result={"orderId": "111", "orderLinkId": "my-link"})
        result = _interp().interpret(response=r)
        assert result.order_link_id == "my-link"

    def test_constructs_bybit_create_order_result(self):
        result = _interp().interpret(response=_make_response())
        assert type(result) is BybitCreateOrderResult

    def test_result_has_exact_order_id_value(self):
        r = _make_response(result={"orderId": "exact-id", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert result.order_id == "exact-id"

    def test_result_has_exact_order_link_id_value(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "exact-link"})
        result = _interp().interpret(response=r)
        assert result.order_link_id == "exact-link"

    def test_preserves_peripheral_spaces_in_order_id(self):
        r = _make_response(result={"orderId": "  spaced  ", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert result.order_id == "  spaced  "

    def test_no_strip_applied_to_order_id(self):
        r = _make_response(result={"orderId": "  abc  ", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert result.order_id == "  abc  "

    def test_does_not_convert_order_id_to_number(self):
        r = _make_response(result={"orderId": "999", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert isinstance(result.order_id, str)

    def test_returns_new_instance_per_call(self):
        interp = _interp()
        r = _make_response()
        res1 = interp.interpret(response=r)
        res2 = interp.interpret(response=r)
        assert res1 is not res2

    def test_equal_inputs_produce_equal_results(self):
        interp = _interp()
        r = _make_response()
        res1 = interp.interpret(response=r)
        res2 = interp.interpret(response=r)
        assert res1 == res2


# ---------------------------------------------------------------------------
# 4. Respuesta rechazada
# ---------------------------------------------------------------------------

class TestRejectedResponse:
    def test_positive_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError):
            _interp().interpret(response=_make_response(ret_code=10001))

    def test_negative_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError):
            _interp().interpret(response=_make_response(ret_code=-1))

    def test_ret_code_1_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError):
            _interp().interpret(response=_make_response(ret_code=1))

    def test_does_not_construct_result_on_rejection(self):
        with pytest.raises(BybitApiError):
            _interp().interpret(response=_make_response(ret_code=10001, result=None))

    def test_does_not_access_result_before_checking_ret_code(self):
        sentinel = object()
        r = _make_response(ret_code=10001, result=sentinel)
        with pytest.raises(BybitApiError):
            _interp().interpret(response=r)

    def test_no_result_mapping_when_ret_code_nonzero(self):
        r = _make_response(ret_code=99, result={"orderId": "x", "orderLinkId": "y"})
        with pytest.raises(BybitApiError):
            _interp().interpret(response=r)

    def test_no_retry_on_rejection(self):
        count = [0]
        original_interpret = BybitCreateOrderResponseInterpreter.interpret

        def counting_interpret(self, *, response):
            count[0] += 1
            return original_interpret(self, response=response)

        BybitCreateOrderResponseInterpreter.interpret = counting_interpret
        try:
            with pytest.raises(BybitApiError):
                _interp().interpret(response=_make_response(ret_code=10001))
        finally:
            BybitCreateOrderResponseInterpreter.interpret = original_interpret

        assert count[0] == 1

    def test_ret_code_conserved_in_error(self):
        r = _make_response(ret_code=10001, ret_msg="some error")
        with pytest.raises(BybitApiError) as exc_info:
            _interp().interpret(response=r)
        assert exc_info.value.ret_code == 10001

    def test_ret_msg_conserved_in_error(self):
        r = _make_response(ret_code=10001, ret_msg="Request parameter error")
        with pytest.raises(BybitApiError) as exc_info:
            _interp().interpret(response=r)
        assert exc_info.value.ret_msg == "Request parameter error"

    def test_error_message_format(self):
        r = _make_response(ret_code=10001, ret_msg="Request parameter error")
        with pytest.raises(BybitApiError) as exc_info:
            _interp().interpret(response=r)
        assert str(exc_info.value) == "Bybit API error 10001: Request parameter error"

    def test_empty_ret_msg_conserved(self):
        r = _make_response(ret_code=10001, ret_msg="")
        with pytest.raises(BybitApiError) as exc_info:
            _interp().interpret(response=r)
        assert exc_info.value.ret_msg == ""

    def test_bybit_api_error_caught_as_exception(self):
        r = _make_response(ret_code=10001, ret_msg="error")
        try:
            _interp().interpret(response=r)
        except Exception as e:
            assert isinstance(e, BybitApiError)
        else:
            pytest.fail("Expected BybitApiError to be raised")

    def test_not_raises_value_error(self):
        r = _make_response(ret_code=10001, ret_msg="error")
        with pytest.raises(BybitApiError):
            try:
                _interp().interpret(response=r)
            except ValueError:
                pytest.fail("must not raise ValueError for rejected responses")


# ---------------------------------------------------------------------------
# 5. Validación de result
# ---------------------------------------------------------------------------

class TestResultValidation:
    def test_accepts_valid_mapping(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert result is not None

    def test_rejects_none_result(self):
        r = _make_response(result=None)
        with pytest.raises(TypeError, match="result must be a mapping"):
            _interp().interpret(response=r)

    def test_rejects_list_result(self):
        r = _make_response(result=[{"orderId": "id", "orderLinkId": "link"}])
        with pytest.raises(TypeError, match="result must be a mapping"):
            _interp().interpret(response=r)

    def test_rejects_string_result(self):
        r = _make_response(result='{"orderId": "id"}')
        with pytest.raises(TypeError, match="result must be a mapping"):
            _interp().interpret(response=r)

    def test_rejects_int_result(self):
        r = _make_response(result=42)
        with pytest.raises(TypeError, match="result must be a mapping"):
            _interp().interpret(response=r)

    def test_rejects_object_result(self):
        r = _make_response(result=object())
        with pytest.raises(TypeError, match="result must be a mapping"):
            _interp().interpret(response=r)

    def test_does_not_modify_mapping(self):
        mapping = {"orderId": "id", "orderLinkId": "link", "extra": "ignored"}
        r = _make_response(result=mapping)
        _interp().interpret(response=r)
        assert "extra" in mapping
        assert len(mapping) == 3

    def test_does_not_add_keys_to_mapping(self):
        mapping = {"orderId": "id", "orderLinkId": "link"}
        original_keys = set(mapping.keys())
        r = _make_response(result=mapping)
        _interp().interpret(response=r)
        assert set(mapping.keys()) == original_keys

    def test_ignores_extra_keys(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "link", "symbol": "BTCUSDT"})
        result = _interp().interpret(response=r)
        assert result.order_id == "id"
        assert result.order_link_id == "link"


# ---------------------------------------------------------------------------
# 6. Claves obligatorias
# ---------------------------------------------------------------------------

class TestRequiredKeys:
    def test_missing_order_id_raises_value_error(self):
        r = _make_response(result={"orderLinkId": "link"})
        with pytest.raises(ValueError, match="orderId"):
            _interp().interpret(response=r)

    def test_missing_order_link_id_raises_value_error(self):
        r = _make_response(result={"orderId": "id"})
        with pytest.raises(ValueError, match="orderLinkId"):
            _interp().interpret(response=r)

    def test_missing_both_raises_value_error(self):
        r = _make_response(result={})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_rejects_snake_case_order_id(self):
        r = _make_response(result={"order_id": "id", "orderLinkId": "link"})
        with pytest.raises(ValueError, match="orderId"):
            _interp().interpret(response=r)

    def test_rejects_snake_case_order_link_id(self):
        r = _make_response(result={"orderId": "id", "order_link_id": "link"})
        with pytest.raises(ValueError, match="orderLinkId"):
            _interp().interpret(response=r)

    def test_no_default_values_for_missing_keys(self):
        r = _make_response(result={"orderLinkId": "link"})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)


# ---------------------------------------------------------------------------
# 7. Tipos de valores extraídos
# ---------------------------------------------------------------------------

class TestValueTypes:
    def test_accepts_str_order_id(self):
        r = _make_response(result={"orderId": "valid-id", "orderLinkId": "link"})
        result = _interp().interpret(response=r)
        assert isinstance(result.order_id, str)

    def test_accepts_str_order_link_id(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "valid-link"})
        result = _interp().interpret(response=r)
        assert isinstance(result.order_link_id, str)

    def test_rejects_int_order_id(self):
        r = _make_response(result={"orderId": 123456789, "orderLinkId": "link"})
        with pytest.raises(TypeError, match="orderId must be str"):
            _interp().interpret(response=r)

    def test_rejects_none_order_id(self):
        r = _make_response(result={"orderId": None, "orderLinkId": "link"})
        with pytest.raises(TypeError, match="orderId must be str"):
            _interp().interpret(response=r)

    def test_rejects_int_order_link_id(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": 42})
        with pytest.raises(TypeError, match="orderLinkId must be str"):
            _interp().interpret(response=r)

    def test_rejects_none_order_link_id(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": None})
        with pytest.raises(TypeError, match="orderLinkId must be str"):
            _interp().interpret(response=r)

    def test_does_not_convert_int_order_id_via_str(self):
        r = _make_response(result={"orderId": 999, "orderLinkId": "link"})
        with pytest.raises(TypeError):
            _interp().interpret(response=r)

    def test_does_not_convert_int_order_link_id_via_str(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": 99})
        with pytest.raises(TypeError):
            _interp().interpret(response=r)


# ---------------------------------------------------------------------------
# 8. Delegación de validaciones al value object
# ---------------------------------------------------------------------------

class TestDelegationToValueObject:
    def test_empty_order_id_propagates(self):
        r = _make_response(result={"orderId": "", "orderLinkId": "link"})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_whitespace_only_order_id_propagates(self):
        r = _make_response(result={"orderId": "   ", "orderLinkId": "link"})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_empty_order_link_id_propagates(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": ""})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_whitespace_only_order_link_id_propagates(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "   "})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_order_link_id_length_37_propagates(self):
        r = _make_response(result={"orderId": "id", "orderLinkId": "x" * 37})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)

    def test_order_link_id_length_36_accepted(self):
        lid = "x" * 36
        r = _make_response(result={"orderId": "id", "orderLinkId": lid})
        result = _interp().interpret(response=r)
        assert result.order_link_id == lid

    def test_value_object_exceptions_propagate_exactly(self):
        r = _make_response(result={"orderId": "", "orderLinkId": "link"})
        with pytest.raises(ValueError):
            _interp().interpret(response=r)


# ---------------------------------------------------------------------------
# 9. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_different_responses_produce_different_results(self):
        interp = _interp()
        r1 = _make_response(result={"orderId": "id-1", "orderLinkId": "link-1"})
        r2 = _make_response(result={"orderId": "id-2", "orderLinkId": "link-2"})
        res1 = interp.interpret(response=r1)
        res2 = interp.interpret(response=r2)
        assert res1.order_id == "id-1"
        assert res2.order_id == "id-2"

    def test_does_not_reuse_previous_result(self):
        interp = _interp()
        r1 = _make_response(result={"orderId": "first", "orderLinkId": "link-1"})
        r2 = _make_response(result={"orderId": "second", "orderLinkId": "link-2"})
        interp.interpret(response=r1)
        res2 = interp.interpret(response=r2)
        assert res2.order_id == "second"

    def test_no_last_result_stored(self):
        interp = _interp()
        interp.interpret(response=_make_response())
        assert not hasattr(interp, "last_result")
        assert not hasattr(interp, "_last_result")

    def test_no_call_counter(self):
        interp = _interp()
        interp.interpret(response=_make_response())
        assert not hasattr(interp, "call_count")
        assert not hasattr(interp, "_call_count")

    def test_no_history_stored(self):
        interp = _interp()
        interp.interpret(response=_make_response())
        assert set(vars(interp)) == set()


# ---------------------------------------------------------------------------
# 10. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_bybit_demo_client(self):
        assert "BybitDemoClient" not in vars(_module)

    def test_does_not_import_create_order_operation(self):
        assert "BybitCreateOrderOperation" not in vars(_module)

    def test_does_not_import_payload_builder(self):
        assert "BybitCreateOrderPayloadBuilder" not in vars(_module)

    def test_does_not_import_endpoint_executor(self):
        assert "BybitEndpointExecutor" not in vars(_module)

    def test_does_not_import_private_api(self):
        assert "BybitPrivateApi" not in vars(_module)

    def test_does_not_import_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)

    def test_does_not_execute_endpoint(self):
        import socket
        calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            _interp().interpret(response=_make_response())
        finally:
            socket.socket.connect = original_connect

        assert calls == []

    def test_does_not_read_env_vars(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel")
        result = _interp().interpret(response=_make_response())
        assert result is not None

    def test_whole_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
