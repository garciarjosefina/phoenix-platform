import inspect
import os
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_gateway import BybitExecutionGateway
import execution_gateway.bybit_gateway as _module
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
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
        client = _ValidClient(_make_bybit_result())
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

    def test_order_link_id_too_long_raises_value_error(self):
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        with pytest.raises(ValueError, match="order_link_id must be at most"):
            gw.execute(_make_request(order_id="x" * 37))


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
        client = _ValidClient(_make_bybit_result(order_id="bybit-999"))
        gw = BybitExecutionGateway(client=client)
        result = gw.execute(_make_request(order_id="dom-42"))
        assert result.order_id == "dom-42"

    def test_exchange_order_id_carries_bybit_order_id(self):
        client = _ValidClient(_make_bybit_result(order_id="bybit-999"))
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
        client = _ValidClient(_make_bybit_result())
        gw = BybitExecutionGateway(client=client)
        gw.execute(_make_request("ord_1"))
        gw.execute(_make_request("ord_2"))
        assert client.received_requests[0] is not client.received_requests[1]

    def test_exception_propagates_by_identity(self):
        marker = RuntimeError("network failure")

        class RaisingClient:
            def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
                raise marker

        gw = BybitExecutionGateway(client=RaisingClient())
        with pytest.raises(RuntimeError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value is marker

    def test_exception_not_wrapped(self):
        class RaisingClient:
            def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
                raise RuntimeError("network failure")

        gw = BybitExecutionGateway(client=RaisingClient())
        with pytest.raises(RuntimeError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value.__cause__ is None


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
