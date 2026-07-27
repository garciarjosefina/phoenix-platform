import inspect
from decimal import Decimal

import pytest

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_response_interpreter import BybitCreateOrderResponseInterpreter
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_response import BybitResponse
import execution_gateway
import execution_gateway.bybit_demo_client_factory as _module


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyExecutor(BybitEndpointExecutor):
    def __init__(self):
        self.calls = []
        self._return_response = _make_response()

    def execute(self, *, endpoint, payload):
        self.calls.append((endpoint, payload))
        return self._return_response


class RejectingExecutor(BybitEndpointExecutor):
    def __init__(self):
        pass

    def execute(self, *, endpoint, payload):
        return _make_response(ret_code=10001, ret_msg="Invalid symbol")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_response(
    ret_code: int = 0,
    ret_msg: str = "OK",
    result: object = None,
) -> BybitResponse:
    if result is None:
        result = {"orderId": "order-123", "orderLinkId": "link-abc"}
    return BybitResponse(
        ret_code=ret_code,
        ret_msg=ret_msg,
        result=result,
        ret_ext_info={},
        time_ms=1000,
    )


def _make_executor() -> SpyExecutor:
    return SpyExecutor()


def _make_request() -> BybitCreateOrderRequest:
    return BybitCreateOrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Market",
        quantity=Decimal("0.001"),
        price=None,
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="test-link-1",
    )


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client as f
        assert f is create_bybit_demo_client

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_client")
        assert execution_gateway.create_bybit_demo_client is create_bybit_demo_client

    def test_included_in_all(self):
        assert "create_bybit_demo_client" in execution_gateway.__all__

    def test_single_factory_for_this_flow(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name)) and "bybit_demo_client" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_demo_client"

    def test_endpoint_executor_kwarg_required(self):
        executor = _make_executor()
        with pytest.raises(TypeError):
            create_bybit_demo_client(executor)

    def test_return_annotation_is_bybit_demo_client(self):
        hints = inspect.get_annotations(create_bybit_demo_client, eval_str=True)
        assert hints.get("return") is BybitDemoClient

    def test_endpoint_executor_param_is_keyword_only(self):
        sig = inspect.signature(create_bybit_demo_client)
        param = sig.parameters["endpoint_executor"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# 2. Validación de entrada
# ---------------------------------------------------------------------------

class TestValidation:
    def test_accepts_valid_executor(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert isinstance(client, BybitDemoClient)

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            create_bybit_demo_client(endpoint_executor=None)

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            create_bybit_demo_client(endpoint_executor={"execute": lambda: None})

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            create_bybit_demo_client(endpoint_executor="executor")

    def test_rejects_arbitrary_object(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            create_bybit_demo_client(endpoint_executor=object())

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="endpoint_executor must be BybitEndpointExecutor"):
            create_bybit_demo_client(endpoint_executor=42)

    def test_does_not_convert_value(self):
        with pytest.raises(TypeError):
            create_bybit_demo_client(endpoint_executor=None)

    def test_does_not_create_executor_internally(self):
        sig = inspect.signature(create_bybit_demo_client)
        assert "endpoint_executor" in sig.parameters
        param = sig.parameters["endpoint_executor"]
        assert param.default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_demo_client(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert isinstance(client, BybitDemoClient)

    def test_returns_exact_type(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert type(client) is BybitDemoClient

    def test_two_calls_return_different_clients(self):
        executor = _make_executor()
        client1 = create_bybit_demo_client(endpoint_executor=executor)
        client2 = create_bybit_demo_client(endpoint_executor=executor)
        assert client1 is not client2

    def test_does_not_return_operation(self):
        result = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert not isinstance(result, BybitCreateOrderOperation)

    def test_does_not_return_tuple(self):
        result = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert not isinstance(result, tuple)

    def test_does_not_return_dict(self):
        result = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert not isinstance(result, dict)

    def test_does_not_return_callable_partial(self):
        import functools
        result = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert not isinstance(result, functools.partial)


# ---------------------------------------------------------------------------
# 4. Grafo de dependencias
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_client_contains_create_order_operation(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert isinstance(client._create_order_operation, BybitCreateOrderOperation)

    def test_operation_contains_payload_builder(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        op = client._create_order_operation
        assert isinstance(op._payload_builder, BybitCreateOrderPayloadBuilder)

    def test_operation_contains_exact_executor(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        op = client._create_order_operation
        assert op._endpoint_executor is executor

    def test_operation_contains_response_interpreter(self):
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        op = client._create_order_operation
        assert isinstance(op._response_interpreter, BybitCreateOrderResponseInterpreter)

    def test_no_component_omitted(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        op = client._create_order_operation
        assert op._payload_builder is not None
        assert op._endpoint_executor is executor
        assert op._response_interpreter is not None

    def test_single_payload_builder_per_client(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        op = client._create_order_operation
        assert type(op._payload_builder) is BybitCreateOrderPayloadBuilder

    def test_single_response_interpreter_per_client(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        op = client._create_order_operation
        assert type(op._response_interpreter) is BybitCreateOrderResponseInterpreter


# ---------------------------------------------------------------------------
# 5. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_clients(self):
        executor = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=executor)
        c2 = create_bybit_demo_client(endpoint_executor=executor)
        assert c1 is not c2

    def test_two_calls_produce_distinct_operations(self):
        executor = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=executor)
        c2 = create_bybit_demo_client(endpoint_executor=executor)
        assert c1._create_order_operation is not c2._create_order_operation

    def test_two_calls_produce_distinct_payload_builders(self):
        executor = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=executor)
        c2 = create_bybit_demo_client(endpoint_executor=executor)
        assert c1._create_order_operation._payload_builder is not c2._create_order_operation._payload_builder

    def test_two_calls_produce_distinct_interpreters(self):
        executor = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=executor)
        c2 = create_bybit_demo_client(endpoint_executor=executor)
        assert c1._create_order_operation._response_interpreter is not c2._create_order_operation._response_interpreter

    def test_same_executor_reused_by_identity(self):
        executor = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=executor)
        c2 = create_bybit_demo_client(endpoint_executor=executor)
        assert c1._create_order_operation._endpoint_executor is executor
        assert c2._create_order_operation._endpoint_executor is executor

    def test_no_global_state_between_calls(self):
        e1 = _make_executor()
        e2 = _make_executor()
        c1 = create_bybit_demo_client(endpoint_executor=e1)
        c2 = create_bybit_demo_client(endpoint_executor=e2)
        assert c1._create_order_operation._endpoint_executor is e1
        assert c2._create_order_operation._endpoint_executor is e2


# ---------------------------------------------------------------------------
# 6. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_executor_not_called_during_construction(self):
        executor = _make_executor()
        create_bybit_demo_client(endpoint_executor=executor)
        assert executor.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_demo_client(endpoint_executor=_make_executor())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "sentinel-secret")
        client = create_bybit_demo_client(endpoint_executor=_make_executor())
        assert isinstance(client, BybitDemoClient)


# ---------------------------------------------------------------------------
# 7. Flujo integrado mínimo
# ---------------------------------------------------------------------------

class TestIntegratedFlow:
    def test_create_order_returns_result(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        result = client.create_order(request=_make_request())
        assert isinstance(result, BybitCreateOrderResult)

    def test_order_id_conserved(self):
        executor = _make_executor()
        executor._return_response = _make_response(
            result={"orderId": "expected-order", "orderLinkId": "expected-link"}
        )
        client = create_bybit_demo_client(endpoint_executor=executor)
        result = client.create_order(request=_make_request())
        assert result.order_id == "expected-order"

    def test_order_link_id_conserved(self):
        executor = _make_executor()
        executor._return_response = _make_response(
            result={"orderId": "oid", "orderLinkId": "my-link"}
        )
        client = create_bybit_demo_client(endpoint_executor=executor)
        result = client.create_order(request=_make_request())
        assert result.order_link_id == "my-link"

    def test_executor_invoked_exactly_once(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        client.create_order(request=_make_request())
        assert len(executor.calls) == 1

    def test_rejected_response_raises_bybit_api_error(self):
        executor = RejectingExecutor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert exc_info.value.ret_code == 10001

    def test_no_retry_on_rejection(self):
        call_count = [0]
        original_execute = RejectingExecutor.execute

        def counting_execute(self, *, endpoint, payload):
            call_count[0] += 1
            return original_execute(self, endpoint=endpoint, payload=payload)

        RejectingExecutor.execute = counting_execute
        try:
            executor = RejectingExecutor()
            client = create_bybit_demo_client(endpoint_executor=executor)
            with pytest.raises(BybitApiError):
                client.create_order(request=_make_request())
        finally:
            RejectingExecutor.execute = original_execute

        assert call_count[0] == 1

    def test_result_type_is_bybit_create_order_result(self):
        executor = _make_executor()
        client = create_bybit_demo_client(endpoint_executor=executor)
        result = client.create_order(request=_make_request())
        assert type(result) is BybitCreateOrderResult


# ---------------------------------------------------------------------------
# 8. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_demo_client)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_demo_client)
        assert "api_secret" not in src
        assert "API_SECRET" not in src

    def test_does_not_know_base_url(self):
        src = inspect.getsource(create_bybit_demo_client)
        assert "base_url" not in src
        assert "bybit.com" not in src

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_contain_endpoint_path(self):
        src = inspect.getsource(_module)
        assert "/v5/order/create" not in src

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_whole_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
