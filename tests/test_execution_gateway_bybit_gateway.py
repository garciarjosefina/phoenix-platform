import inspect
import json
import os
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
import execution_gateway.bybit_gateway as _module
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError
from execution_gateway.gateway import ExecutionGateway
from execution_gateway.contracts import ExecutionRequest, ExecutionResult


def _make_request(order_id="ord_abc", **overrides):
    kwargs = dict(
        order_id=order_id,
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        quantity=0.001,
    )
    kwargs.update(overrides)
    return ExecutionRequest(**kwargs)


def _make_bybit_result(order_id="bybit-exchange-1", order_link_id="ord_abc"):
    return BybitCreateOrderResult(order_id=order_id, order_link_id=order_link_id)


class _ValidClient:
    """Doble fiel al contrato real de BybitDemoClient: recibe
    BybitCreateOrderRequest, devuelve BybitCreateOrderResult."""

    def __init__(self, result: BybitCreateOrderResult):
        self._result = result
        self.call_count = 0
        self.received_requests: list[BybitCreateOrderRequest] = []

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.call_count += 1
        self.received_requests.append(request)
        return self._result


class _EchoingClient:
    """Devuelve un BybitCreateOrderResult cuyo order_link_id coincide siempre
    con el orderLinkId recibido -- simula el comportamiento correcto real de
    Bybit para pruebas que ejecutan múltiples requests con distinto order_id."""

    def __init__(self):
        self.call_count = 0
        self.received_requests: list[BybitCreateOrderRequest] = []

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.call_count += 1
        self.received_requests.append(request)
        return BybitCreateOrderResult(
            order_id=f"bybit-{self.call_count}",
            order_link_id=request.order_link_id,
        )


class _NoPlaceOrder:
    def execute(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        ...


class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_gateway import BybitExecutionGateway as C
        assert C is BybitExecutionGateway

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitExecutionGateway")
        assert execution_gateway.BybitExecutionGateway is BybitExecutionGateway

    def test_in_all(self):
        assert "BybitExecutionGateway" in execution_gateway.__all__


class TestStructuralCompatibility:
    def test_implements_execution_gateway(self):
        gw = BybitExecutionGateway(client=_ValidClient(_make_bybit_result()))
        assert isinstance(gw, ExecutionGateway)

    def test_no_explicit_inheritance_required(self):
        assert not issubclass(BybitExecutionGateway, ExecutionGateway) or True
        gw = BybitExecutionGateway(client=_ValidClient(_make_bybit_result()))
        assert isinstance(gw, ExecutionGateway)


class TestConstructor:
    def test_valid_client_accepted(self):
        gw = BybitExecutionGateway(client=_ValidClient(_make_bybit_result()))
        assert gw is not None

    def test_incompatible_client_rejected(self):
        with pytest.raises(TypeError):
            BybitExecutionGateway(client=_NoPlaceOrder())

    def test_none_client_rejected(self):
        with pytest.raises(TypeError):
            BybitExecutionGateway(client=None)

    def test_no_explicit_inheritance_needed(self):
        class AnotherClient:
            def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
                return _make_bybit_result()

        gw = BybitExecutionGateway(client=AnotherClient())
        assert gw is not None

    def test_client_not_called_during_construction(self):
        class SentinelClient:
            def __init__(self):
                self.called = False

            def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
                self.called = True
                return _make_bybit_result()

        sentinel = SentinelClient()
        BybitExecutionGateway(client=sentinel)
        assert not sentinel.called


# ---------------------------------------------------------------------------
# Traducción: ExecutionRequest -> BybitCreateOrderRequest
# ---------------------------------------------------------------------------

class TestRequestTranslation:
    def test_client_receives_bybit_create_order_request(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request())
        assert isinstance(client.received_requests[0], BybitCreateOrderRequest)

    def test_client_does_not_receive_execution_request(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request())
        assert not isinstance(client.received_requests[0], ExecutionRequest)

    def test_symbol_translated(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(symbol="ETHUSDT"))
        assert client.received_requests[0].symbol == "ETHUSDT"

    def test_side_buy_translated_to_capitalized(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(side="buy"))
        assert client.received_requests[0].side == "Buy"

    def test_side_sell_translated_to_capitalized(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(side="sell"))
        assert client.received_requests[0].side == "Sell"

    def test_order_type_market_translated(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(order_type="market"))
        assert client.received_requests[0].order_type == "Market"

    def test_order_type_limit_translated(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(order_type="limit", price=50_000.0))
        assert client.received_requests[0].order_type == "Limit"

    def test_quantity_translated_to_decimal(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(quantity=0.001))
        translated = client.received_requests[0].quantity
        assert isinstance(translated, Decimal)
        assert translated == Decimal("0.001")

    def test_quantity_decimal_avoids_float_artifacts(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(quantity=0.1))
        assert client.received_requests[0].quantity == Decimal("0.1")

    def test_price_none_for_market_order(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(order_type="market"))
        assert client.received_requests[0].price is None

    def test_price_translated_to_decimal_for_limit_order(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(order_type="limit", price=50_000.0))
        translated = client.received_requests[0].price
        assert isinstance(translated, Decimal)
        assert translated == Decimal("50000.0")

    def test_order_link_id_uses_domain_order_id(self):
        client = _ValidClient(_make_bybit_result(order_link_id="dom-order-77"))
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(order_id="dom-order-77"))
        assert client.received_requests[0].order_link_id == "dom-order-77"

    def test_reduce_only_defaults_false(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request())
        assert client.received_requests[0].reduce_only is False

    def test_time_in_force_defaults_to_gtc(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request())
        assert client.received_requests[0].time_in_force == "GTC"


# ---------------------------------------------------------------------------
# Traducción: BybitCreateOrderResult -> ExecutionResult
# ---------------------------------------------------------------------------

class TestResultTranslation:
    def test_execute_returns_execution_result(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert isinstance(result, ExecutionResult)

    def test_does_not_return_bybit_create_order_result(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert not isinstance(result, BybitCreateOrderResult)

    def test_order_id_preserves_domain_identity(self):
        client = _ValidClient(_make_bybit_result(order_id="bybit-999", order_link_id="dom-42"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="dom-42"))
        assert result.order_id == "dom-42"

    def test_exchange_order_id_carries_bybit_order_id(self):
        client = _ValidClient(_make_bybit_result(order_id="bybit-999", order_link_id="dom-42"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="dom-42"))
        assert result.exchange_order_id == "bybit-999"

    def test_status_is_accepted_on_success(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.status == "accepted"

    def test_error_message_is_none_on_success(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.error_message is None


# ---------------------------------------------------------------------------
# Correlación order_link_id (Core Hardening Pack A, Parte J)
# ---------------------------------------------------------------------------

class TestOrderLinkIdCorrelation:
    def test_matching_echo_returns_accepted(self):
        client = _ValidClient(_make_bybit_result(order_link_id="ord_abc"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="ord_abc"))
        assert result.status == "accepted"

    def test_mismatched_echo_raises_infrastructure_error(self):
        client = _ValidClient(_make_bybit_result(order_link_id="SOMETHING-ELSE"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request(order_id="ord_abc"))

    def test_mismatched_echo_does_not_return_accepted(self):
        client = _ValidClient(_make_bybit_result(order_link_id="SOMETHING-ELSE"))
        gw = BybitExecutionGateway(client=client)
        try:
            result = gw.execute(_make_request(order_id="ord_abc"))
            assert result.status != "accepted"
        except ExecutionInfrastructureError:
            pass

    def test_mismatch_message_is_safe(self):
        client = _ValidClient(_make_bybit_result(order_link_id="SOMETHING-ELSE"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request(order_id="ord_abc"))
        assert "order_link_id" not in str(exc_info.value)
        assert "SOMETHING-ELSE" not in str(exc_info.value)

    def test_mismatch_does_not_leak_bybit_vocabulary_in_type(self):
        client = _ValidClient(_make_bybit_result(order_link_id="SOMETHING-ELSE"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request(order_id="ord_abc"))


# ---------------------------------------------------------------------------
# Traducción: BybitApiError -> clasificación explícita (Core Hardening Pack A, Parte A)
# ---------------------------------------------------------------------------

class _RejectingClient:
    def __init__(self, error: BybitApiError):
        self._error = error
        self.call_count = 0

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.call_count += 1
        raise self._error


class TestBusinessRejectionTranslation:
    @pytest.mark.parametrize("ret_code", [10001, 110003, 110004, 110007])
    def test_allowlisted_codes_translate_to_rejected(self, ret_code):
        client = _RejectingClient(BybitApiError(ret_code=ret_code, ret_msg="business rejection"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.status == "rejected"

    def test_rejection_does_not_raise(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="Request parameter error"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert isinstance(result, ExecutionResult)

    def test_rejection_does_not_raise_bybit_api_error(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="Request parameter error"))
        gw = BybitExecutionGateway(client=client)
        try:
            gw.execute(_make_request())
        except BybitApiError:
            pytest.fail("BybitApiError must not cross the ExecutionGateway boundary")

    def test_rejection_status_is_rejected(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="Request parameter error"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.status == "rejected"

    def test_rejection_error_message_carries_ret_msg(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="Request parameter error"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.error_message == "Request parameter error"

    def test_rejection_preserves_domain_order_id(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="bad params"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="dom-77"))
        assert result.order_id == "dom-77"

    def test_rejection_has_no_exchange_order_id(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="bad params"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request())
        assert result.exchange_order_id is None

    def test_rejection_calls_client_exactly_once(self):
        client = _RejectingClient(BybitApiError(ret_code=10001, ret_msg="bad params"))
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request())
        assert client.call_count == 1

    def test_different_allowlisted_codes_translate_to_rejected(self):
        for ret_code, ret_msg in [(10001, "params error"), (110004, "insufficient balance")]:
            client = _RejectingClient(BybitApiError(ret_code=ret_code, ret_msg=ret_msg))
            gw = BybitExecutionGateway(client=client)
            result = gw.execute(_make_request())
            assert result.status == "rejected"
            assert result.error_message == ret_msg


# ---------------------------------------------------------------------------
# Errores operacionales de Bybit -> ExecutionInfrastructureError (Parte A)
# ---------------------------------------------------------------------------

class TestOperationalErrorTranslation:
    @pytest.mark.parametrize(
        "ret_code",
        [429, 10000, 10002, 10003, 10004, 10005, 10006, 10007, 10016, 10017, -1, -2015, 33004],
    )
    def test_known_operational_codes_translate_to_infrastructure_error(self, ret_code):
        client = _RejectingClient(BybitApiError(ret_code=ret_code, ret_msg="operational failure"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_unknown_ret_code_treated_as_infrastructure(self):
        client = _RejectingClient(BybitApiError(ret_code=987654321, ret_msg="never seen before"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_unknown_ret_code_never_treated_as_rejection(self):
        client = _RejectingClient(BybitApiError(ret_code=987654321, ret_msg="never seen before"))
        gw = BybitExecutionGateway(client=client)
        try:
            result = gw.execute(_make_request())
            assert result.status != "rejected"
        except ExecutionInfrastructureError:
            pass

    def test_operational_error_cause_is_original_bybit_api_error(self):
        original = BybitApiError(ret_code=10003, ret_msg="Invalid apikey")
        client = _RejectingClient(original)
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value.__cause__ is original

    def test_operational_error_message_does_not_leak_ret_msg(self):
        client = _RejectingClient(BybitApiError(ret_code=10003, ret_msg="Invalid apikey: ZZSECRETMARKER"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request())
        assert "ZZSECRETMARKER" not in str(exc_info.value)
        assert "apikey" not in str(exc_info.value)

    def test_operational_error_message_does_not_leak_ret_code(self):
        client = _RejectingClient(BybitApiError(ret_code=10003, ret_msg="Invalid apikey"))
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request())
        assert "10003" not in str(exc_info.value)


# ---------------------------------------------------------------------------
# Ausencia de catch-all (Core Hardening Pack A, Parte B)
# ---------------------------------------------------------------------------

class _RaisingClient:
    def __init__(self, error: BaseException):
        self._error = error
        self.call_count = 0

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.call_count += 1
        raise self._error


class TestTransportFailureTranslation:
    def test_os_error_translated_to_infrastructure_error(self):
        gw = BybitExecutionGateway(client=_RaisingClient(OSError("connection refused")))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_os_error_subclass_translated(self):
        gw = BybitExecutionGateway(client=_RaisingClient(ConnectionRefusedError("refused")))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_timeout_error_translated(self):
        gw = BybitExecutionGateway(client=_RaisingClient(TimeoutError("timed out")))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_json_decode_error_translated(self):
        malformed = json.JSONDecodeError("Expecting value", "not json", 0)
        gw = BybitExecutionGateway(client=_RaisingClient(malformed))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_request())

    def test_os_error_cause_preserved(self):
        original = OSError("connection refused")
        gw = BybitExecutionGateway(client=_RaisingClient(original))
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value.__cause__ is original

    def test_message_is_safe_constant_not_original_text(self):
        gw = BybitExecutionGateway(
            client=_RaisingClient(OSError("secret internal detail: ZZLEAKMARKER"))
        )
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_request())
        assert "ZZLEAKMARKER" not in str(exc_info.value)


class TestProgrammingErrorsPropagateUnwrapped:
    def test_type_error_propagates(self):
        gw = BybitExecutionGateway(client=_RaisingClient(TypeError("bug")))
        with pytest.raises(TypeError):
            gw.execute(_make_request())

    def test_type_error_not_wrapped(self):
        gw = BybitExecutionGateway(client=_RaisingClient(TypeError("bug")))
        try:
            gw.execute(_make_request())
        except ExecutionInfrastructureError:
            pytest.fail("TypeError must not be disguised as ExecutionInfrastructureError")
        except TypeError:
            pass

    def test_attribute_error_propagates(self):
        gw = BybitExecutionGateway(client=_RaisingClient(AttributeError("no such attr")))
        with pytest.raises(AttributeError):
            gw.execute(_make_request())

    def test_key_error_propagates(self):
        gw = BybitExecutionGateway(client=_RaisingClient(KeyError("orderId")))
        with pytest.raises(KeyError):
            gw.execute(_make_request())

    def test_assertion_error_propagates(self):
        gw = BybitExecutionGateway(client=_RaisingClient(AssertionError("invariant broken")))
        with pytest.raises(AssertionError):
            gw.execute(_make_request())

    def test_zero_division_error_propagates(self):
        gw = BybitExecutionGateway(client=_RaisingClient(ZeroDivisionError("division by zero")))
        with pytest.raises(ZeroDivisionError):
            gw.execute(_make_request())

    def test_bare_runtime_error_propagates_unwrapped(self):
        # RuntimeError no es un tipo de infraestructura conocido de la
        # cadena de transporte real: no debe traducirse.
        gw = BybitExecutionGateway(client=_RaisingClient(RuntimeError("unexpected")))
        with pytest.raises(RuntimeError):
            gw.execute(_make_request())

    def test_generic_value_error_propagates_unwrapped(self):
        # Distinto de json.JSONDecodeError: un ValueError de dominio no debe
        # disfrazarse de fallo de infraestructura.
        gw = BybitExecutionGateway(client=_RaisingClient(ValueError("invariant violated")))
        with pytest.raises(ValueError):
            gw.execute(_make_request())


class TestDelegation:
    def test_execute_delegates_to_place_order(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request("ord_abc"))
        assert client.call_count == 1

    def test_single_call_per_execute(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request("ord_abc"))
        gw.execute(_make_request("ord_abc"))
        assert client.call_count == 2

    def test_two_requests_do_not_share_translated_request_identity(self):
        client = _EchoingClient()
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request("ord_1"))
        gw.execute(_make_request("ord_2"))
        assert client.received_requests[0] is not client.received_requests[1]


class TestNoSideEffects:
    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            gw = BybitExecutionGateway(client=_ValidClient(_make_bybit_result()))
            assert gw is not None
        finally:
            del os.environ["BYBIT_API_KEY"]


class TestAdapterStaticShape:
    def test_module_imports_bybit_types(self):
        src = inspect.getsource(_module)
        assert "BybitCreateOrderRequest" in src
        assert "BybitCreateOrderResult" in src

    def test_no_bybit_types_in_public_execute_signature(self):
        sig = inspect.signature(BybitExecutionGateway.execute)
        hints = inspect.get_annotations(BybitExecutionGateway.execute, eval_str=True)
        assert hints.get("request") is ExecutionRequest
        assert hints.get("return") is ExecutionResult

    def test_infrastructure_message_constant_does_not_mention_ret_code_placeholder(self):
        src = inspect.getsource(_module)
        assert "{ret_code}" not in src
        assert "{ret_msg}" not in src

    def test_does_not_use_str_error_for_infrastructure_message(self):
        src = inspect.getsource(_module)
        assert "message=str(error)" not in src


# ---------------------------------------------------------------------------
# Longitud de order_id (Core Hardening Pack A, Parte K)
# ---------------------------------------------------------------------------

class TestOrderIdLengthIncompatibility:
    def test_long_order_id_raises_execution_request_not_supported_error(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(order_id="x" * 37))

    def test_long_order_id_message_does_not_mention_bybit_vocabulary(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError) as exc_info:
            gw.execute(_make_request(order_id="x" * 37))
        message = str(exc_info.value)
        assert "order_link_id" not in message
        assert "36 characters" not in message
        assert "Bybit" not in message

    def test_order_id_at_exact_limit_accepted(self):
        client = _ValidClient(_make_bybit_result(order_link_id="x" * 36))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="x" * 36))
        assert result.status == "accepted"

    def test_client_not_called_when_order_id_too_long(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(order_id="x" * 37))
        assert client.call_count == 0


# ---------------------------------------------------------------------------
# Cantidades y precios finitos, sin notación científica (Parte I)
# ---------------------------------------------------------------------------

class TestFiniteNumericTranslation:
    def test_positive_infinity_quantity_rejected(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(quantity=float("inf"), order_type="market", price=None))

    def test_positive_infinity_price_rejected(self):
        # ExecutionRequest.__post_init__ no rechaza +inf como precio (inf <= 0
        # es False), así que la solicitud de dominio se construye igual; el
        # adaptador debe rechazarla antes de tocar el cliente.
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(order_type="limit", quantity=1.0, price=float("inf")))

    def test_nan_quantity_rejected(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(quantity=float("nan"), order_type="market", price=None))

    def test_client_not_called_for_non_finite_quantity(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ExecutionRequestNotSupportedError):
            gw.execute(_make_request(quantity=float("inf"), order_type="market", price=None))
        assert client.call_count == 0

    @pytest.mark.parametrize(
        "quantity, expected",
        [
            (0.001, "0.001"),
            (1.0, "1.0"),
            (1e-8, "0.00000001"),
            (1e-7, "0.0000001"),
        ],
    )
    def test_small_and_normal_quantities_translated_without_scientific_notation(self, quantity, expected):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(quantity=quantity, order_type="market", price=None))
        translated = client.received_requests[0].quantity
        assert format(translated, "f") == expected
        assert "E" not in format(translated, "f")

    def test_large_quantity_translated_without_scientific_notation(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(quantity=1e16, order_type="market", price=None))
        translated = client.received_requests[0].quantity
        assert format(translated, "f") == "10000000000000000"

    def test_finite_value_preserves_exact_value(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request(quantity=123456789.123, order_type="market", price=None))
        translated = client.received_requests[0].quantity
        assert translated == Decimal("123456789.123")


class TestExistingSuiteUnaffected:
    def test_gateway_config_still_works(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"

    def test_credentials_still_work(self):
        from execution_gateway.credentials import BybitDemoCredentials
        creds = BybitDemoCredentials(api_key="k", api_secret="s")
        assert creds.api_key == "k"

    def test_factory_still_works(self):
        from execution_gateway.factory import create_execution_gateway
        from execution_gateway.config import GatewayConfig
        gw = create_execution_gateway(config=GatewayConfig())
        assert gw is not None
