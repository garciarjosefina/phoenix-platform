from decimal import Decimal

import pytest

from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_response import BybitResponse
import execution_gateway
import execution_gateway.bybit_client as _module


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyOperation(BybitCreateOrderOperation):
    def __init__(self):
        self.calls = []
        self._return_value = _make_response()

    def execute(self, *, request):
        self.calls.append(request)
        return self._return_value


class FailingOperation(BybitCreateOrderOperation):
    def __init__(self):
        pass

    def execute(self, *, request):
        raise RuntimeError("operation failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(ret_code: int = 0) -> BybitResponse:
    return BybitResponse(
        ret_code=ret_code,
        ret_msg="OK",
        result={"orderId": "abc123"},
        ret_ext_info={},
        time_ms=1000,
    )


def _market_request(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Market",
        quantity=Decimal("0.001"),
        price=None,
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="test-market-1",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


def _limit_request(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Limit",
        quantity=Decimal("0.001"),
        price=Decimal("42000.00"),
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="test-limit-1",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


def _make_client(op: BybitCreateOrderOperation | None = None) -> BybitDemoClient:
    return BybitDemoClient(create_order_operation=op or SpyOperation())


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_client import BybitDemoClient as C
        assert C is BybitDemoClient

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitDemoClient")
        assert execution_gateway.BybitDemoClient is BybitDemoClient

    def test_in_all(self):
        assert "BybitDemoClient" in execution_gateway.__all__

    def test_no_second_client_class(self):
        client_classes = [
            v for k, v in vars(_module).items()
            if isinstance(v, type) and "client" in k.lower() and v is not BybitDemoClient
        ]
        assert client_classes == []


# ---------------------------------------------------------------------------
# 2. Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_valid_construction(self):
        client = BybitDemoClient(create_order_operation=SpyOperation())
        assert client is not None

    def test_stores_operation(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        assert client._create_order_operation is op

    def test_rejects_invalid_operation(self):
        with pytest.raises(TypeError, match="create_order_operation must be BybitCreateOrderOperation"):
            BybitDemoClient(create_order_operation=object())

    def test_rejects_none_operation(self):
        with pytest.raises(TypeError, match="create_order_operation must be BybitCreateOrderOperation"):
            BybitDemoClient(create_order_operation=None)

    def test_rejects_str_operation(self):
        with pytest.raises(TypeError, match="create_order_operation must be BybitCreateOrderOperation"):
            BybitDemoClient(create_order_operation="op")

    def test_does_not_call_operation_during_construction(self):
        op = SpyOperation()
        BybitDemoClient(create_order_operation=op)
        assert op.calls == []

    def test_no_internally_created_operation(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        assert client._create_order_operation is op

    def test_only_one_instance_var(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        assert set(vars(client)) == {"_create_order_operation"}

    def test_does_not_read_env_vars(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "should-not-be-read")
        monkeypatch.setenv("BYBIT_API_SECRET", "should-not-be-read")
        client = _make_client()
        assert client is not None

    def test_structural_isinstance_still_works(self):
        class WithPlaceOrder:
            def place_order(self, request): ...

        assert isinstance(WithPlaceOrder(), BybitDemoClient)

    def test_client_instance_is_instance_of_itself(self):
        client = _make_client()
        assert isinstance(client, BybitDemoClient)


# ---------------------------------------------------------------------------
# 3. Método create_order
# ---------------------------------------------------------------------------

class TestCreateOrderMethod:
    def test_method_exists(self):
        client = _make_client()
        assert hasattr(client, "create_order")
        assert callable(client.create_order)

    def test_request_is_keyword_only(self):
        client = _make_client()
        with pytest.raises(TypeError):
            client.create_order(_market_request())

    def test_accepts_market_request(self):
        client = _make_client()
        result = client.create_order(request=_market_request())
        assert result is not None

    def test_accepts_limit_request(self):
        client = _make_client()
        result = client.create_order(request=_limit_request())
        assert result is not None

    def test_rejects_none_request(self):
        client = _make_client()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            client.create_order(request=None)

    def test_rejects_dict_request(self):
        client = _make_client()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            client.create_order(request={"symbol": "BTCUSDT"})

    def test_rejects_str_request(self):
        client = _make_client()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            client.create_order(request="BTCUSDT")


# ---------------------------------------------------------------------------
# 4. Delegación
# ---------------------------------------------------------------------------

class TestDelegation:
    def test_delegates_to_operation_once(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        client.create_order(request=_market_request())
        assert len(op.calls) == 1

    def test_passes_request_by_identity(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        r = _market_request()
        client.create_order(request=r)
        assert op.calls[0] is r

    def test_returns_response_by_identity(self):
        expected = _make_response()
        op = SpyOperation()
        op._return_value = expected
        client = BybitDemoClient(create_order_operation=op)
        result = client.create_order(request=_market_request())
        assert result is expected

    def test_does_not_create_second_response(self):
        responses = []
        class TrackingOp(BybitCreateOrderOperation):
            def __init__(self): pass
            def execute(self, *, request):
                r = _make_response()
                responses.append(r)
                return r

        client = BybitDemoClient(create_order_operation=TrackingOp())
        returned = client.create_order(request=_market_request())
        assert returned is responses[0]
        assert len(responses) == 1

    def test_does_not_modify_request(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        r = _market_request(symbol="BTCUSDT")
        client.create_order(request=r)
        assert r.symbol == "BTCUSDT"

    def test_does_not_copy_request(self):
        op = SpyOperation()
        client = BybitDemoClient(create_order_operation=op)
        r = _market_request()
        client.create_order(request=r)
        assert op.calls[0] is r

    def test_does_not_call_payload_builder_directly(self):
        import execution_gateway.bybit_client as mod
        assert "BybitCreateOrderPayloadBuilder" not in vars(mod)

    def test_does_not_call_endpoint_executor_directly(self):
        import execution_gateway.bybit_client as mod
        assert "BybitEndpointExecutor" not in vars(mod)

    def test_does_not_use_bybit_create_order_endpoint_directly(self):
        import execution_gateway.bybit_client as mod
        assert "BYBIT_CREATE_ORDER_ENDPOINT" not in vars(mod)


# ---------------------------------------------------------------------------
# 5. Respuesta
# ---------------------------------------------------------------------------

class TestResponse:
    def test_returns_success_response_by_identity(self):
        expected = _make_response(ret_code=0)
        op = SpyOperation()
        op._return_value = expected
        client = _make_client(op)
        assert client.create_order(request=_market_request()) is expected

    def test_returns_rejected_response_by_identity(self):
        rejected = _make_response(ret_code=10001)
        op = SpyOperation()
        op._return_value = rejected
        client = _make_client(op)
        assert client.create_order(request=_market_request()) is rejected

    def test_does_not_raise_on_nonzero_ret_code(self):
        op = SpyOperation()
        op._return_value = _make_response(ret_code=10001)
        client = _make_client(op)
        result = client.create_order(request=_market_request())
        assert result.ret_code == 10001

    def test_does_not_inspect_ret_code(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert "ret_code" not in src

    def test_does_not_inspect_ret_msg(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert "ret_msg" not in src

    def test_does_not_inspect_result_field(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert ".result" not in src

    def test_does_not_extract_order_id(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert "orderId" not in src
        assert "order_id" not in src


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_each_call_delegates_again(self):
        op = SpyOperation()
        client = _make_client(op)
        client.create_order(request=_market_request())
        client.create_order(request=_market_request())
        assert len(op.calls) == 2

    def test_no_cached_response(self):
        r1 = _make_response(ret_code=0)
        r2 = _make_response(ret_code=10001)
        responses = [r1, r2]
        idx = [0]

        class SequentialOp(BybitCreateOrderOperation):
            def __init__(self): pass
            def execute(self, *, request):
                r = responses[idx[0]]
                idx[0] += 1
                return r

        client = BybitDemoClient(create_order_operation=SequentialOp())
        assert client.create_order(request=_market_request()) is r1
        assert client.create_order(request=_market_request()) is r2

    def test_different_requests_forwarded_independently(self):
        op = SpyOperation()
        client = _make_client(op)
        r1 = _market_request(symbol="BTCUSDT")
        r2 = _market_request(symbol="ETHUSDT")
        client.create_order(request=r1)
        client.create_order(request=r2)
        assert op.calls[0] is r1
        assert op.calls[1] is r2

    def test_no_history_stored(self):
        op = SpyOperation()
        client = _make_client(op)
        client.create_order(request=_market_request())
        client.create_order(request=_market_request())
        assert set(vars(client)) == {"_create_order_operation"}

    def test_no_call_counter(self):
        op = SpyOperation()
        client = _make_client(op)
        client.create_order(request=_market_request())
        assert not hasattr(client, "call_count")
        assert not hasattr(client, "_call_count")


# ---------------------------------------------------------------------------
# 7. Errores
# ---------------------------------------------------------------------------

class TestErrors:
    def test_exception_propagates_exactly(self):
        client = BybitDemoClient(create_order_operation=FailingOperation())
        with pytest.raises(RuntimeError, match="operation failed"):
            client.create_order(request=_market_request())

    def test_no_retry(self):
        count = [0]

        class CountingOp(BybitCreateOrderOperation):
            def __init__(self): pass
            def execute(self, *, request):
                count[0] += 1
                raise RuntimeError("fail")

        client = BybitDemoClient(create_order_operation=CountingOp())
        with pytest.raises(RuntimeError):
            client.create_order(request=_market_request())
        assert count[0] == 1

    def test_does_not_transform_exception(self):
        class WeirdOp(BybitCreateOrderOperation):
            def __init__(self): pass
            def execute(self, *, request):
                raise ValueError("weird")

        client = BybitDemoClient(create_order_operation=WeirdOp())
        with pytest.raises(ValueError, match="weird"):
            client.create_order(request=_market_request())

    def test_no_second_call_on_failure(self):
        op = FailingOperation()
        client = BybitDemoClient(create_order_operation=op)
        call_count = [0]
        original_execute = op.execute

        def counting_execute(*, request):
            call_count[0] += 1
            return original_execute(request=request)

        op.execute = counting_execute
        with pytest.raises(RuntimeError):
            client.create_order(request=_market_request())
        assert call_count[0] == 1


# ---------------------------------------------------------------------------
# 8. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_create_order_has_no_path_string(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert '"/v5/order/create"' not in src
        assert "'/v5/order/create'" not in src

    def test_create_order_has_no_post_string(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert '"POST"' not in src
        assert "'POST'" not in src

    def test_create_order_has_no_category_string(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert '"category"' not in src
        assert "'category'" not in src

    def test_create_order_has_no_linear_string(self):
        import inspect
        src = inspect.getsource(BybitDemoClient.create_order)
        assert '"linear"' not in src
        assert "'linear'" not in src

    def test_no_sender_import(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_no_parser_import(self):
        assert "BybitResponseParser" not in vars(_module)

    def test_no_authenticator_import(self):
        assert "StandardBybitAuthenticator" not in vars(_module)
        assert "BybitAuthenticator" not in vars(_module)

    def test_no_signer_import(self):
        assert "HmacSha256Signer" not in vars(_module)

    def test_no_serializer_import(self):
        assert "StandardJsonSerializer" not in vars(_module)

    def test_no_url_builder_import(self):
        assert "BybitUrlBuilder" not in vars(_module)

    def test_no_header_builder_import(self):
        assert "BybitHeaderBuilder" not in vars(_module)

    def test_whole_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
