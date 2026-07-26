from decimal import Decimal

import pytest

from execution_gateway import (
    BybitCreateOrderOperation,
    BybitCreateOrderPayloadBuilder,
    BybitCreateOrderRequest,
    BybitEndpointExecutor,
    BybitResponse,
    BYBIT_CREATE_ORDER_ENDPOINT,
)
from execution_gateway import bybit_create_order_operation as _module


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyPayloadBuilder(BybitCreateOrderPayloadBuilder):
    def __init__(self):
        self.calls = []
        self._return_value = {"category": "linear", "symbol": "BTCUSDT", "side": "Buy"}

    def build(self, *, request):
        self.calls.append(request)
        return self._return_value


class SpyEndpointExecutor(BybitEndpointExecutor):
    def __init__(self):
        self.calls = []
        self._return_value = _make_response()

    def execute(self, *, endpoint, payload):
        self.calls.append((endpoint, payload))
        return self._return_value


class FailingPayloadBuilder(BybitCreateOrderPayloadBuilder):
    def __init__(self):
        pass

    def build(self, *, request):
        raise RuntimeError("builder failed")


class FailingEndpointExecutor(BybitEndpointExecutor):
    def __init__(self):
        pass

    def execute(self, *, endpoint, payload):
        raise RuntimeError("executor failed")


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


def _make_op(
    builder: BybitCreateOrderPayloadBuilder | None = None,
    executor: BybitEndpointExecutor | None = None,
) -> BybitCreateOrderOperation:
    return BybitCreateOrderOperation(
        payload_builder=builder or SpyPayloadBuilder(),
        endpoint_executor=executor or SpyEndpointExecutor(),
    )


# ---------------------------------------------------------------------------
# 1. Importación y API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_class_importable_directly(self):
        from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
        assert BybitCreateOrderOperation is not None

    def test_class_importable_from_package(self):
        from execution_gateway import BybitCreateOrderOperation
        assert BybitCreateOrderOperation is not None

    def test_included_in_all(self):
        import execution_gateway
        assert "BybitCreateOrderOperation" in execution_gateway.__all__

    def test_construction_with_valid_deps(self):
        op = _make_op()
        assert op is not None

    def test_only_execute_public_method(self):
        op = _make_op()
        public = {n for n in dir(op) if not n.startswith("_")}
        assert public == {"execute"}


# ---------------------------------------------------------------------------
# 2. Constructor
# ---------------------------------------------------------------------------

class TestConstructor:
    def test_stores_payload_builder(self):
        b = SpyPayloadBuilder()
        op = BybitCreateOrderOperation(
            payload_builder=b,
            endpoint_executor=SpyEndpointExecutor(),
        )
        assert op._payload_builder is b

    def test_stores_endpoint_executor(self):
        e = SpyEndpointExecutor()
        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=e,
        )
        assert op._endpoint_executor is e

    def test_rejects_invalid_payload_builder(self):
        with pytest.raises(TypeError, match="payload_builder must be BybitCreateOrderPayloadBuilder"):
            BybitCreateOrderOperation(
                payload_builder=object(),
                endpoint_executor=SpyEndpointExecutor(),
            )

    def test_rejects_none_payload_builder(self):
        with pytest.raises(TypeError, match="payload_builder must be BybitCreateOrderPayloadBuilder"):
            BybitCreateOrderOperation(
                payload_builder=None,
                endpoint_executor=SpyEndpointExecutor(),
            )

    def test_rejects_invalid_endpoint_executor(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            BybitCreateOrderOperation(
                payload_builder=SpyPayloadBuilder(),
                endpoint_executor=object(),
            )

    def test_rejects_none_endpoint_executor(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            BybitCreateOrderOperation(
                payload_builder=SpyPayloadBuilder(),
                endpoint_executor=None,
            )

    def test_does_not_call_builder_during_construction(self):
        b = SpyPayloadBuilder()
        BybitCreateOrderOperation(
            payload_builder=b,
            endpoint_executor=SpyEndpointExecutor(),
        )
        assert b.calls == []

    def test_does_not_call_executor_during_construction(self):
        e = SpyEndpointExecutor()
        BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=e,
        )
        assert e.calls == []

    def test_no_internally_created_dependencies(self):
        b = SpyPayloadBuilder()
        e = SpyEndpointExecutor()
        op = BybitCreateOrderOperation(payload_builder=b, endpoint_executor=e)
        assert op._payload_builder is b
        assert op._endpoint_executor is e

    def test_does_not_read_env_vars(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "should-not-be-read")
        monkeypatch.setenv("BYBIT_API_SECRET", "should-not-be-read")
        op = _make_op()
        assert op is not None


# ---------------------------------------------------------------------------
# 3. Entrada
# ---------------------------------------------------------------------------

class TestInput:
    def test_execute_is_keyword_only(self):
        op = _make_op()
        r = _market_request()
        with pytest.raises(TypeError):
            op.execute(r)

    def test_rejects_none_request(self):
        op = _make_op()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            op.execute(request=None)

    def test_rejects_dict_request(self):
        op = _make_op()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            op.execute(request={"symbol": "BTCUSDT"})

    def test_rejects_str_request(self):
        op = _make_op()
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            op.execute(request="BTCUSDT")

    def test_accepts_valid_market_request(self):
        op = _make_op()
        result = op.execute(request=_market_request())
        assert result is not None

    def test_accepts_valid_limit_request(self):
        op = _make_op()
        result = op.execute(request=_limit_request())
        assert result is not None


# ---------------------------------------------------------------------------
# 4. Orden y composición
# ---------------------------------------------------------------------------

class TestComposition:
    def test_builder_called_before_executor(self):
        order = []

        class OrderedBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                order.append("builder")
                return {}

        class OrderedExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                order.append("executor")
                return _make_response()

        op = BybitCreateOrderOperation(
            payload_builder=OrderedBuilder(),
            endpoint_executor=OrderedExecutor(),
        )
        op.execute(request=_market_request())
        assert order == ["builder", "executor"]

    def test_builder_called_exactly_once(self):
        b = SpyPayloadBuilder()
        op = _make_op(builder=b)
        op.execute(request=_market_request())
        assert len(b.calls) == 1

    def test_executor_called_exactly_once(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        assert len(e.calls) == 1

    def test_request_sent_by_identity_to_builder(self):
        b = SpyPayloadBuilder()
        op = _make_op(builder=b)
        r = _market_request()
        op.execute(request=r)
        assert b.calls[0] is r

    def test_payload_sent_by_identity_to_executor(self):
        payload = {"category": "linear", "symbol": "BTCUSDT"}

        class FixedBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request): return payload

        e = SpyEndpointExecutor()
        op = BybitCreateOrderOperation(
            payload_builder=FixedBuilder(),
            endpoint_executor=e,
        )
        op.execute(request=_market_request())
        _, received_payload = e.calls[0]
        assert received_payload is payload

    def test_uses_bybit_create_order_endpoint(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        received_endpoint, _ = e.calls[0]
        assert received_endpoint is BYBIT_CREATE_ORDER_ENDPOINT

    def test_response_returned_by_identity(self):
        expected = _make_response()

        class FixedExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload): return expected

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=FixedExecutor(),
        )
        result = op.execute(request=_market_request())
        assert result is expected

    def test_does_not_create_second_response(self):
        results = []

        class TrackingExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                r = _make_response()
                results.append(r)
                return r

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=TrackingExecutor(),
        )
        returned = op.execute(request=_market_request())
        assert returned is results[0]
        assert len(results) == 1

    def test_does_not_modify_request(self):
        r = _market_request()
        original_symbol = r.symbol
        original_qty = r.quantity
        _make_op().execute(request=r)
        assert r.symbol == original_symbol
        assert r.quantity == original_qty

    def test_does_not_modify_payload(self):
        captured_payload = {}

        class CapturingBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                p = {"category": "linear", "qty": "0.001"}
                captured_payload.update(p)
                return p

        class CheckingExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                assert payload == captured_payload
                return _make_response()

        op = BybitCreateOrderOperation(
            payload_builder=CapturingBuilder(),
            endpoint_executor=CheckingExecutor(),
        )
        op.execute(request=_market_request())


# ---------------------------------------------------------------------------
# 5. Endpoint
# ---------------------------------------------------------------------------

class TestEndpoint:
    def test_does_not_create_new_endpoint(self):
        import execution_gateway.bybit_create_order_operation as mod
        import ast, inspect
        src = inspect.getsource(mod)
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "BybitEndpoint":
                    pytest.fail("BybitCreateOrderOperation must not create a new BybitEndpoint")
                if isinstance(func, ast.Attribute) and func.attr == "BybitEndpoint":
                    pytest.fail("BybitCreateOrderOperation must not create a new BybitEndpoint")

    def test_does_not_accept_endpoint_as_argument(self):
        import inspect
        sig = inspect.signature(BybitCreateOrderOperation.execute)
        assert "endpoint" not in sig.parameters

    def test_does_not_hardcode_post_string(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert '"POST"' not in src
        assert "'POST'" not in src

    def test_does_not_hardcode_path_string(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert '"/v5/order/create"' not in src
        assert "'/v5/order/create'" not in src

    def test_endpoint_is_bybit_create_order_endpoint(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        received_endpoint, _ = e.calls[0]
        assert received_endpoint.method == "POST"
        assert received_endpoint.path == "/v5/order/create"

    def test_market_and_limit_use_same_endpoint(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        op.execute(request=_limit_request())
        endpoint_m, _ = e.calls[0]
        endpoint_l, _ = e.calls[1]
        assert endpoint_m is endpoint_l


# ---------------------------------------------------------------------------
# 6. Payload
# ---------------------------------------------------------------------------

class TestPayload:
    def test_does_not_duplicate_mapping(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert '"category"' not in src
        assert "'category'" not in src
        assert '"orderType"' not in src
        assert "'orderType'" not in src

    def test_does_not_serialize_to_json(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert "json" not in src
        assert "dumps" not in src
        assert "loads" not in src

    def test_does_not_convert_payload_to_string(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        _, payload = e.calls[0]
        assert isinstance(payload, dict)

    def test_does_not_copy_payload(self):
        payload_ref = [None]

        class RefBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                p = {"category": "linear"}
                payload_ref[0] = p
                return p

        e = SpyEndpointExecutor()
        op = BybitCreateOrderOperation(
            payload_builder=RefBuilder(),
            endpoint_executor=e,
        )
        op.execute(request=_market_request())
        _, received = e.calls[0]
        assert received is payload_ref[0]


# ---------------------------------------------------------------------------
# 7. Respuesta
# ---------------------------------------------------------------------------

class TestResponse:
    def test_does_not_inspect_ret_code(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert "ret_code" not in src

    def test_does_not_inspect_ret_msg(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert "ret_msg" not in src

    def test_does_not_inspect_result(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert ".result" not in src

    def test_does_not_extract_order_id(self):
        import inspect
        src = inspect.getsource(BybitCreateOrderOperation.execute)
        assert "orderId" not in src
        assert "order_id" not in src

    def test_returns_success_response_by_identity(self):
        expected = _make_response(ret_code=0)

        class FixedExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload): return expected

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=FixedExecutor(),
        )
        assert op.execute(request=_market_request()) is expected

    def test_returns_rejected_response_by_identity(self):
        rejected = _make_response(ret_code=10001)

        class FixedExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload): return rejected

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=FixedExecutor(),
        )
        assert op.execute(request=_market_request()) is rejected

    def test_does_not_raise_on_nonzero_ret_code(self):
        class ErrorExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                return _make_response(ret_code=10001)

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=ErrorExecutor(),
        )
        result = op.execute(request=_market_request())
        assert result.ret_code == 10001


# ---------------------------------------------------------------------------
# 8. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_each_call_invokes_builder_again(self):
        b = SpyPayloadBuilder()
        op = _make_op(builder=b)
        op.execute(request=_market_request())
        op.execute(request=_market_request())
        assert len(b.calls) == 2

    def test_each_call_invokes_executor_again(self):
        e = SpyEndpointExecutor()
        op = _make_op(executor=e)
        op.execute(request=_market_request())
        op.execute(request=_market_request())
        assert len(e.calls) == 2

    def test_order_maintained_on_each_call(self):
        call_order = []

        class Ordered(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                call_order.append("builder")
                return {}

        class OrderedEx(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                call_order.append("executor")
                return _make_response()

        op = BybitCreateOrderOperation(
            payload_builder=Ordered(),
            endpoint_executor=OrderedEx(),
        )
        op.execute(request=_market_request())
        op.execute(request=_market_request())
        assert call_order == ["builder", "executor", "builder", "executor"]

    def test_different_requests_handled_independently(self):
        b = SpyPayloadBuilder()
        op = _make_op(builder=b)
        r1 = _market_request(symbol="BTCUSDT")
        r2 = _market_request(symbol="ETHUSDT")
        op.execute(request=r1)
        op.execute(request=r2)
        assert b.calls[0] is r1
        assert b.calls[1] is r2

    def test_different_responses_returned_correctly(self):
        responses = [_make_response(ret_code=0), _make_response(ret_code=10001)]
        idx = [0]

        class MultiExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                r = responses[idx[0]]
                idx[0] += 1
                return r

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=MultiExecutor(),
        )
        assert op.execute(request=_market_request()) is responses[0]
        assert op.execute(request=_market_request()) is responses[1]


# ---------------------------------------------------------------------------
# 9. Errores
# ---------------------------------------------------------------------------

class TestErrors:
    def test_builder_exception_propagates_exactly(self):
        op = BybitCreateOrderOperation(
            payload_builder=FailingPayloadBuilder(),
            endpoint_executor=SpyEndpointExecutor(),
        )
        with pytest.raises(RuntimeError, match="builder failed"):
            op.execute(request=_market_request())

    def test_executor_not_called_when_builder_fails(self):
        e = SpyEndpointExecutor()
        op = BybitCreateOrderOperation(
            payload_builder=FailingPayloadBuilder(),
            endpoint_executor=e,
        )
        with pytest.raises(RuntimeError):
            op.execute(request=_market_request())
        assert e.calls == []

    def test_executor_exception_propagates_exactly(self):
        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=FailingEndpointExecutor(),
        )
        with pytest.raises(RuntimeError, match="executor failed"):
            op.execute(request=_market_request())

    def test_no_retry_on_builder_failure(self):
        build_count = [0]

        class CountingBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                build_count[0] += 1
                raise RuntimeError("fail")

        op = BybitCreateOrderOperation(
            payload_builder=CountingBuilder(),
            endpoint_executor=SpyEndpointExecutor(),
        )
        with pytest.raises(RuntimeError):
            op.execute(request=_market_request())
        assert build_count[0] == 1

    def test_no_retry_on_executor_failure(self):
        exec_count = [0]

        class CountingExecutor(BybitEndpointExecutor):
            def __init__(self): pass
            def execute(self, *, endpoint, payload):
                exec_count[0] += 1
                raise RuntimeError("fail")

        op = BybitCreateOrderOperation(
            payload_builder=SpyPayloadBuilder(),
            endpoint_executor=CountingExecutor(),
        )
        with pytest.raises(RuntimeError):
            op.execute(request=_market_request())
        assert exec_count[0] == 1

    def test_does_not_transform_exceptions(self):
        class WeirdBuilder(BybitCreateOrderPayloadBuilder):
            def __init__(self): pass
            def build(self, *, request):
                raise ValueError("weird error")

        op = BybitCreateOrderOperation(
            payload_builder=WeirdBuilder(),
            endpoint_executor=SpyEndpointExecutor(),
        )
        with pytest.raises(ValueError, match="weird error"):
            op.execute(request=_market_request())


# ---------------------------------------------------------------------------
# 10. Ausencia de estado y responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoStateAndNoExtraResponsibilities:
    def test_no_last_request_stored(self):
        op = _make_op()
        op.execute(request=_market_request())
        assert not hasattr(op, "last_request")
        assert not hasattr(op, "_last_request")

    def test_no_last_payload_stored(self):
        op = _make_op()
        op.execute(request=_market_request())
        assert not hasattr(op, "last_payload")
        assert not hasattr(op, "_last_payload")

    def test_no_last_response_stored(self):
        op = _make_op()
        op.execute(request=_market_request())
        assert not hasattr(op, "last_response")
        assert not hasattr(op, "_last_response")

    def test_no_last_endpoint_stored(self):
        op = _make_op()
        op.execute(request=_market_request())
        assert not hasattr(op, "last_endpoint")
        assert not hasattr(op, "_last_endpoint")

    def test_only_two_instance_vars(self):
        op = _make_op()
        assert set(vars(op)) == {"_payload_builder", "_endpoint_executor"}

    def test_does_not_import_http_transport(self):
        src_vars = vars(_module)
        assert "UrllibHttpTransport" not in src_vars
        assert "HttpTransport" not in src_vars

    def test_does_not_import_authenticator(self):
        src_vars = vars(_module)
        assert "StandardBybitAuthenticator" not in src_vars
        assert "BybitAuthenticator" not in src_vars

    def test_does_not_import_signer(self):
        src_vars = vars(_module)
        assert "HmacSha256Signer" not in src_vars
        assert "MessageSigner" not in src_vars

    def test_does_not_import_serializer(self):
        src_vars = vars(_module)
        assert "StandardJsonSerializer" not in src_vars
        assert "JsonSerializer" not in src_vars

    def test_does_not_import_header_builder(self):
        src_vars = vars(_module)
        assert "BybitHeaderBuilder" not in src_vars

    def test_does_not_import_request_sender(self):
        src_vars = vars(_module)
        assert "BybitPrivateRequestSender" not in src_vars

    def test_does_not_import_url_builder(self):
        src_vars = vars(_module)
        assert "BybitUrlBuilder" not in src_vars
