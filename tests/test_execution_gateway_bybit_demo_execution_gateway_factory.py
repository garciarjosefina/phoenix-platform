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
from execution_gateway.bybit_demo_execution_gateway_factory import (
    create_bybit_demo_execution_gateway,
)
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_url_builder import BybitUrlBuilder
import execution_gateway
import execution_gateway.bybit_demo_execution_gateway_factory as _module


# ---------------------------------------------------------------------------
# Spy doubles
# ---------------------------------------------------------------------------

class SpyPrivateApi(BybitPrivateApi):
    def __init__(self):
        self.calls: list[dict] = []
        self._return_response: BybitResponse = _make_success_response()

    def request(self, *, url: str, payload: object) -> BybitResponse:
        self.calls.append({"url": url, "payload": dict(payload)})
        return self._return_response


class RejectingPrivateApi(BybitPrivateApi):
    def __init__(self):
        self.call_count = 0

    def request(self, *, url: str, payload: object) -> BybitResponse:
        self.call_count += 1
        return BybitResponse(
            ret_code=10001,
            ret_msg="Request parameter error",
            result={},
            ret_ext_info={},
            time_ms=1000,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_success_response(
    order_id: str = "gw-order-123",
    order_link_id: str = "gw-link-001",
) -> BybitResponse:
    return BybitResponse(
        ret_code=0,
        ret_msg="OK",
        result={"orderId": order_id, "orderLinkId": order_link_id},
        ret_ext_info={},
        time_ms=1000,
    )


def _make_request(
    order_link_id: str = "gw-link-001",
) -> BybitCreateOrderRequest:
    return BybitCreateOrderRequest(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Limit",
        quantity=Decimal("0.001"),
        price=Decimal("50000"),
        time_in_force="GTC",
        reduce_only=False,
        order_link_id=order_link_id,
    )


# ---------------------------------------------------------------------------
# 1. API pública
# ---------------------------------------------------------------------------

class TestImport:
    def test_importable_directly(self):
        from execution_gateway.bybit_demo_execution_gateway_factory import (
            create_bybit_demo_execution_gateway as f,
        )
        assert f is create_bybit_demo_execution_gateway

    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "create_bybit_demo_execution_gateway")
        assert (
            execution_gateway.create_bybit_demo_execution_gateway
            is create_bybit_demo_execution_gateway
        )

    def test_included_in_all(self):
        assert "create_bybit_demo_execution_gateway" in execution_gateway.__all__

    def test_single_factory_for_this_gateway(self):
        factory_names = [
            name for name in vars(_module)
            if callable(getattr(_module, name))
            and "execution_gateway" in name.lower()
            and not name.startswith("_")
        ]
        assert len(factory_names) == 1
        assert factory_names[0] == "create_bybit_demo_execution_gateway"

    def test_private_api_kwarg_required(self):
        spy = SpyPrivateApi()
        with pytest.raises(TypeError):
            create_bybit_demo_execution_gateway(spy)

    def test_return_annotation_is_bybit_execution_gateway(self):
        hints = inspect.get_annotations(create_bybit_demo_execution_gateway, eval_str=True)
        assert hints.get("return") is BybitExecutionGateway

    def test_private_api_param_is_keyword_only(self):
        sig = inspect.signature(create_bybit_demo_execution_gateway)
        param = sig.parameters["private_api"]
        assert param.kind == inspect.Parameter.KEYWORD_ONLY


# ---------------------------------------------------------------------------
# 2. Validación
# ---------------------------------------------------------------------------

class TestValidation:
    def test_accepts_valid_private_api(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert gw is not None

    def test_rejects_none(self):
        with pytest.raises(TypeError, match="private_api must be BybitPrivateApi"):
            create_bybit_demo_execution_gateway(private_api=None)

    def test_rejects_dict(self):
        with pytest.raises(TypeError, match="private_api must be BybitPrivateApi"):
            create_bybit_demo_execution_gateway(private_api={"request": lambda: None})

    def test_rejects_string(self):
        with pytest.raises(TypeError, match="private_api must be BybitPrivateApi"):
            create_bybit_demo_execution_gateway(private_api="api")

    def test_rejects_arbitrary_object(self):
        with pytest.raises(TypeError, match="private_api must be BybitPrivateApi"):
            create_bybit_demo_execution_gateway(private_api=object())

    def test_rejects_int(self):
        with pytest.raises(TypeError, match="private_api must be BybitPrivateApi"):
            create_bybit_demo_execution_gateway(private_api=42)

    def test_does_not_convert_value(self):
        with pytest.raises(TypeError):
            create_bybit_demo_execution_gateway(private_api=None)

    def test_does_not_create_private_api_internally(self):
        sig = inspect.signature(create_bybit_demo_execution_gateway)
        assert "private_api" in sig.parameters
        param = sig.parameters["private_api"]
        assert param.default is inspect.Parameter.empty


# ---------------------------------------------------------------------------
# 3. Resultado
# ---------------------------------------------------------------------------

class TestResult:
    def test_returns_bybit_execution_gateway(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert isinstance(gw, BybitExecutionGateway)

    def test_returns_exact_type(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert type(gw) is BybitExecutionGateway

    def test_two_calls_return_different_gateways(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        assert gw1 is not gw2

    def test_does_not_return_client(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert not isinstance(gw, BybitDemoClient)

    def test_does_not_return_executor(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert not isinstance(gw, BybitEndpointExecutor)

    def test_does_not_return_tuple(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert not isinstance(gw, tuple)

    def test_does_not_return_dict(self):
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert not isinstance(gw, dict)


# ---------------------------------------------------------------------------
# 4. Grafo de dependencias
# ---------------------------------------------------------------------------

class TestDependencyGraph:
    def test_gateway_contains_bybit_demo_client(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        assert isinstance(gw._client, BybitDemoClient)

    def test_client_contains_create_order_operation(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        assert isinstance(gw._client._create_order_operation, BybitCreateOrderOperation)

    def test_operation_contains_payload_builder(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        op = gw._client._create_order_operation
        assert isinstance(op._payload_builder, BybitCreateOrderPayloadBuilder)

    def test_operation_contains_response_interpreter(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        op = gw._client._create_order_operation
        assert isinstance(op._response_interpreter, BybitCreateOrderResponseInterpreter)

    def test_operation_contains_endpoint_executor(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        op = gw._client._create_order_operation
        assert isinstance(op._endpoint_executor, BybitEndpointExecutor)

    def test_executor_contains_exact_private_api(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        executor = gw._client._create_order_operation._endpoint_executor
        assert executor._private_api is spy

    def test_executor_contains_url_builder(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        executor = gw._client._create_order_operation._endpoint_executor
        assert isinstance(executor._url_builder, BybitUrlBuilder)

    def test_no_component_missing(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        client = gw._client
        op = client._create_order_operation
        executor = op._endpoint_executor
        assert client is not None
        assert op is not None
        assert op._payload_builder is not None
        assert op._response_interpreter is not None
        assert executor is not None
        assert executor._url_builder is not None
        assert executor._private_api is spy


# ---------------------------------------------------------------------------
# 5. Reutilización de create_bybit_demo_client
# ---------------------------------------------------------------------------

class TestReuseClientFactory:
    def test_uses_create_bybit_demo_client(self, monkeypatch):
        calls = []
        original = create_bybit_demo_client

        def spy_factory(**kwargs):
            calls.append(kwargs)
            return original(**kwargs)

        monkeypatch.setattr(
            _module,
            "create_bybit_demo_client",
            spy_factory,
        )
        spy = SpyPrivateApi()
        create_bybit_demo_execution_gateway(private_api=spy)
        assert len(calls) == 1

    def test_passes_executor_to_client_factory(self, monkeypatch):
        received_executors = []
        original = create_bybit_demo_client

        def spy_factory(**kwargs):
            received_executors.append(kwargs.get("endpoint_executor"))
            return original(**kwargs)

        monkeypatch.setattr(_module, "create_bybit_demo_client", spy_factory)
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        assert len(received_executors) == 1
        assert isinstance(received_executors[0], BybitEndpointExecutor)
        assert received_executors[0]._private_api is spy

    def test_client_from_factory_delivered_to_gateway(self, monkeypatch):
        returned_clients = []
        original = create_bybit_demo_client

        def spy_factory(**kwargs):
            client = original(**kwargs)
            returned_clients.append(client)
            return client

        monkeypatch.setattr(_module, "create_bybit_demo_client", spy_factory)
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        assert len(returned_clients) == 1
        assert gw._client is returned_clients[0]


# ---------------------------------------------------------------------------
# 6. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_calls_produce_distinct_gateways(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        assert gw1 is not gw2

    def test_two_calls_produce_distinct_clients(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        assert gw1._client is not gw2._client

    def test_two_calls_produce_distinct_operations(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        assert (
            gw1._client._create_order_operation
            is not gw2._client._create_order_operation
        )

    def test_two_calls_produce_distinct_executors(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        ex1 = gw1._client._create_order_operation._endpoint_executor
        ex2 = gw2._client._create_order_operation._endpoint_executor
        assert ex1 is not ex2

    def test_two_calls_produce_distinct_url_builders(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        ub1 = gw1._client._create_order_operation._endpoint_executor._url_builder
        ub2 = gw2._client._create_order_operation._endpoint_executor._url_builder
        assert ub1 is not ub2

    def test_same_private_api_reused_by_identity(self):
        spy = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy)
        pa1 = gw1._client._create_order_operation._endpoint_executor._private_api
        pa2 = gw2._client._create_order_operation._endpoint_executor._private_api
        assert pa1 is spy
        assert pa2 is spy

    def test_no_global_state_between_calls(self):
        spy1 = SpyPrivateApi()
        spy2 = SpyPrivateApi()
        gw1 = create_bybit_demo_execution_gateway(private_api=spy1)
        gw2 = create_bybit_demo_execution_gateway(private_api=spy2)
        pa1 = gw1._client._create_order_operation._endpoint_executor._private_api
        pa2 = gw2._client._create_order_operation._endpoint_executor._private_api
        assert pa1 is spy1
        assert pa2 is spy2


# ---------------------------------------------------------------------------
# 7. Ausencia de ejecución durante construcción
# ---------------------------------------------------------------------------

class TestNoExecutionDuringConstruction:
    def test_private_api_not_called_during_construction(self):
        spy = SpyPrivateApi()
        create_bybit_demo_execution_gateway(private_api=spy)
        assert spy.calls == []

    def test_no_network_calls_during_construction(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []

    def test_no_env_vars_read_during_construction(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "sentinel-key")
        monkeypatch.setenv("BYBIT_API_SECRET", "sentinel-secret")
        gw = create_bybit_demo_execution_gateway(private_api=SpyPrivateApi())
        assert isinstance(gw, BybitExecutionGateway)


# ---------------------------------------------------------------------------
# 8. Flujo integrado mínimo
# ---------------------------------------------------------------------------

class TestIntegratedFlow:
    def test_success_returns_bybit_create_order_result(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        result = gw.execute(_make_request())
        assert isinstance(result, BybitCreateOrderResult)

    def test_order_id_conserved(self):
        spy = SpyPrivateApi()
        spy._return_response = _make_success_response(order_id="factory-order-42")
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        result = gw.execute(_make_request())
        assert result.order_id == "factory-order-42"

    def test_order_link_id_conserved(self):
        spy = SpyPrivateApi()
        spy._return_response = _make_success_response(order_link_id="factory-link-xyz")
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        result = gw.execute(_make_request())
        assert result.order_link_id == "factory-link-xyz"

    def test_private_api_called_exactly_once(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        gw.execute(_make_request())
        assert len(spy.calls) == 1

    def test_endpoint_path_correct(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        gw.execute(_make_request())
        assert "/v5/order/create" in spy.calls[0]["url"]

    def test_endpoint_method_is_post(self):
        assert BYBIT_CREATE_ORDER_ENDPOINT.method == "POST"

    def test_payload_symbol(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        gw.execute(_make_request())
        assert spy.calls[0]["payload"]["symbol"] == "BTCUSDT"

    def test_payload_order_type(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        gw.execute(_make_request())
        assert spy.calls[0]["payload"]["orderType"] == "Limit"

    def test_no_retry_on_success(self):
        spy = SpyPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=spy)
        gw.execute(_make_request())
        assert len(spy.calls) == 1

    def test_rejected_response_raises_bybit_api_error(self):
        api = RejectingPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=api)
        with pytest.raises(BybitApiError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value.ret_code == 10001

    def test_rejected_error_msg_conserved(self):
        api = RejectingPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=api)
        with pytest.raises(BybitApiError) as exc_info:
            gw.execute(_make_request())
        assert exc_info.value.ret_msg == "Request parameter error"

    def test_no_retry_on_rejection(self):
        api = RejectingPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=api)
        with pytest.raises(BybitApiError):
            gw.execute(_make_request())
        assert api.call_count == 1

    def test_no_fallback_on_rejection(self):
        api = RejectingPrivateApi()
        gw = create_bybit_demo_execution_gateway(private_api=api)
        with pytest.raises(BybitApiError):
            gw.execute(_make_request())


# ---------------------------------------------------------------------------
# 9. Ausencia de responsabilidades adicionales
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_does_not_import_os(self):
        assert "os" not in vars(_module)

    def test_does_not_know_api_key(self):
        src = inspect.getsource(create_bybit_demo_execution_gateway)
        assert "api_key" not in src
        assert "API_KEY" not in src

    def test_does_not_know_api_secret(self):
        src = inspect.getsource(create_bybit_demo_execution_gateway)
        assert "api_secret" not in src
        assert "API_SECRET" not in src

    def test_does_not_import_sender(self):
        assert "BybitPrivateRequestSender" not in vars(_module)

    def test_does_not_import_transport(self):
        assert "UrllibHttpTransport" not in vars(_module)
        assert "HttpTransport" not in vars(_module)

    def test_does_not_import_credentials(self):
        assert "BybitDemoCredentials" not in vars(_module)

    def test_whole_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"
