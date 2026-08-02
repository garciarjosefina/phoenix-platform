"""
Prueba integrada de creación de orden de punta a punta.

Sección A — desde BybitDemoClient.create_order() con SpyExecutor:
  BybitDemoClient.create_order()
  → BybitCreateOrderOperation
  → BybitCreateOrderPayloadBuilder
  → BybitEndpointExecutor   ← SpyExecutor (frontera simulada)
  → BybitResponse
  → BybitCreateOrderResponseInterpreter
  → BybitCreateOrderResult

Sección B — desde BybitExecutionGateway.execute() con SpyPrivateApi:
  BybitExecutionGateway.execute(ExecutionRequest)     ← Port del dominio
  → traducción interna a BybitCreateOrderRequest       (adaptador)
  → BybitDemoClient.place_order()
  → BybitDemoClient.create_order()
  → BybitCreateOrderOperation
  → BybitCreateOrderPayloadBuilder
  → BybitEndpointExecutor (real)
  → BybitUrlBuilder (real)
  → BybitPrivateApi   ← SpyPrivateApi (frontera simulada)
  → BybitResponse
  → BybitCreateOrderResponseInterpreter
  → BybitCreateOrderResult
  → traducción interna a ExecutionResult               (adaptador)
"""
from decimal import Decimal

import pytest

from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_response_interpreter import BybitCreateOrderResponseInterpreter
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client
from execution_gateway.bybit_endpoint_executor import BybitEndpointExecutor
from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.bybit_private_api import BybitPrivateApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.contracts import ExecutionRequest, ExecutionResult
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError


# ---------------------------------------------------------------------------
# Spy — único doble permitido (frontera de infraestructura)
# ---------------------------------------------------------------------------

class SpyExecutor(BybitEndpointExecutor):
    """Sustituye la red. No reemplaza ningún componente de lógica."""

    def __init__(self):
        self.calls: list[dict] = []
        self._return_response: BybitResponse = _make_success_response()

    def execute(self, *, endpoint, payload):
        self.calls.append({"endpoint": endpoint, "payload": dict(payload)})
        return self._return_response


class ErrorExecutor(BybitEndpointExecutor):
    """Lanza una excepción arbitraria para simular fallo de infraestructura."""

    def __init__(self, error: BaseException):
        self._error = error
        self.call_count = 0

    def execute(self, *, endpoint, payload):
        self.call_count += 1
        raise self._error


class RejectingExecutor(BybitEndpointExecutor):
    """Devuelve una respuesta rechazada por la API."""

    def __init__(self):
        self.call_count = 0

    def execute(self, *, endpoint, payload):
        self.call_count += 1
        return _make_rejected_response()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_success_response(
    order_id: str = "bybit-order-123",
    order_link_id: str = "phoenix-test-order-001",
) -> BybitResponse:
    return BybitResponse(
        ret_code=0,
        ret_msg="OK",
        result={"orderId": order_id, "orderLinkId": order_link_id},
        ret_ext_info={},
        time_ms=1000,
    )


def _make_rejected_response() -> BybitResponse:
    return BybitResponse(
        ret_code=10001,
        ret_msg="Request parameter error",
        result={},
        ret_ext_info={},
        time_ms=1000,
    )


def _make_request(
    order_link_id: str = "phoenix-test-order-001",
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


def _build_client(executor: BybitEndpointExecutor) -> BybitDemoClient:
    return create_bybit_demo_client(endpoint_executor=executor)


# ---------------------------------------------------------------------------
# 1. Importación y composición
# ---------------------------------------------------------------------------

class TestComposition:
    def test_client_factory_importable(self):
        from execution_gateway.bybit_demo_client_factory import create_bybit_demo_client as f
        assert f is create_bybit_demo_client

    def test_client_importable(self):
        from execution_gateway.bybit_client import BybitDemoClient as C
        assert C is BybitDemoClient

    def test_full_composition_valid(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        assert isinstance(client, BybitDemoClient)

    def test_no_real_component_omitted(self):
        from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
        from execution_gateway.bybit_create_order_payload_builder import BybitCreateOrderPayloadBuilder
        executor = SpyExecutor()
        client = _build_client(executor)
        op = client._create_order_operation
        assert isinstance(op, BybitCreateOrderOperation)
        assert isinstance(op._payload_builder, BybitCreateOrderPayloadBuilder)
        assert isinstance(op._response_interpreter, BybitCreateOrderResponseInterpreter)
        assert op._endpoint_executor is executor

    def test_spy_only_at_infrastructure_boundary(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        op = client._create_order_operation
        assert type(op._endpoint_executor) is SpyExecutor


# ---------------------------------------------------------------------------
# 2. Flujo exitoso
# ---------------------------------------------------------------------------

class TestSuccessFlow:
    def test_gateway_accepts_request(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert result is not None

    def test_returns_bybit_create_order_result(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert isinstance(result, BybitCreateOrderResult)

    def test_order_id_conserved(self):
        executor = SpyExecutor()
        executor._return_response = _make_success_response(order_id="bybit-order-123")
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert result.order_id == "bybit-order-123"

    def test_order_link_id_conserved(self):
        executor = SpyExecutor()
        executor._return_response = _make_success_response(
            order_link_id="phoenix-test-order-001"
        )
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert result.order_link_id == "phoenix-test-order-001"

    def test_executor_called_exactly_once(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert len(executor.calls) == 1

    def test_correct_endpoint_sent(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["endpoint"] is BYBIT_CREATE_ORDER_ENDPOINT

    def test_endpoint_method_is_post(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["endpoint"].method == "POST"

    def test_payload_category(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["category"] == "linear"

    def test_payload_symbol(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["symbol"] == "BTCUSDT"

    def test_payload_side(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["side"] == "Buy"

    def test_payload_order_type(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["orderType"] == "Limit"

    def test_payload_qty(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["qty"] == "0.001"

    def test_payload_price(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["price"] == "50000"

    def test_payload_order_link_id(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert executor.calls[0]["payload"]["orderLinkId"] == "phoenix-test-order-001"

    def test_does_not_return_bybit_response(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert not isinstance(result, BybitResponse)

    def test_does_not_return_dict(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert not isinstance(result, dict)

    def test_order_link_id_not_lost(self):
        executor = SpyExecutor()
        executor._return_response = _make_success_response(order_link_id="my-unique-link")
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert result.order_link_id == "my-unique-link"

    def test_no_network_calls(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            executor = SpyExecutor()
            client = _build_client(executor)
            client.create_order(request=_make_request())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []

    def test_no_retries_on_success(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request())
        assert len(executor.calls) == 1


# ---------------------------------------------------------------------------
# 3. Rechazo de API
# ---------------------------------------------------------------------------

class TestApiRejection:
    def test_propagates_bybit_api_error(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError):
            client.create_order(request=_make_request())

    def test_error_ret_code_conserved(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert exc_info.value.ret_code == 10001

    def test_error_ret_msg_conserved(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert exc_info.value.ret_msg == "Request parameter error"

    def test_error_message_format(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert str(exc_info.value) == "Bybit API error 10001: Request parameter error"

    def test_executor_called_exactly_once_on_rejection(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError):
            client.create_order(request=_make_request())
        assert executor.call_count == 1

    def test_no_retry_on_rejection(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError):
            client.create_order(request=_make_request())
        assert executor.call_count == 1

    def test_no_fallback_returned(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError):
            result = client.create_order(request=_make_request())

    def test_does_not_return_create_order_result(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        caught = None
        try:
            client.create_order(request=_make_request())
        except BybitApiError as e:
            caught = e
        assert caught is not None
        assert not isinstance(caught, BybitCreateOrderResult)

    def test_does_not_access_order_id_on_rejection(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert not hasattr(exc_info.value, "order_id")

    def test_does_not_access_order_link_id_on_rejection(self):
        executor = RejectingExecutor()
        client = _build_client(executor)
        with pytest.raises(BybitApiError) as exc_info:
            client.create_order(request=_make_request())
        assert not hasattr(exc_info.value, "order_link_id")


# ---------------------------------------------------------------------------
# 4. Error de infraestructura
# ---------------------------------------------------------------------------

class TestInfrastructureError:
    def test_exception_propagates_by_identity(self):
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError) as exc_info:
            client.create_order(request=_make_request())
        assert exc_info.value is transport_error

    def test_exception_not_wrapped(self):
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError):
            client.create_order(request=_make_request())

    def test_exception_not_transformed_to_bybit_api_error(self):
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError):
            try:
                client.create_order(request=_make_request())
            except BybitApiError:
                pytest.fail("RuntimeError must not be converted to BybitApiError")

    def test_no_retry_on_transport_error(self):
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError):
            client.create_order(request=_make_request())
        assert executor.call_count == 1

    def test_executor_called_exactly_once_on_error(self):
        transport_error = OSError("connection refused")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(OSError):
            client.create_order(request=_make_request())
        assert executor.call_count == 1

    def test_interpreter_not_called_on_transport_error(self, monkeypatch):
        calls = []
        original = BybitCreateOrderResponseInterpreter.interpret
        monkeypatch.setattr(
            BybitCreateOrderResponseInterpreter,
            "interpret",
            lambda self, *, response: calls.append(response) or original(self, response=response),
        )
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError):
            client.create_order(request=_make_request())
        assert calls == []

    def test_no_fallback_on_transport_error(self):
        transport_error = RuntimeError("simulated transport failure")
        executor = ErrorExecutor(transport_error)
        client = _build_client(executor)
        with pytest.raises(RuntimeError):
            client.create_order(request=_make_request())


# ---------------------------------------------------------------------------
# 5. Múltiples llamadas
# ---------------------------------------------------------------------------

class TestMultipleCalls:
    def test_two_requests_produce_two_distinct_results(self):
        executor = SpyExecutor()
        executor._return_response = _make_success_response(
            order_id="order-A", order_link_id="link-A"
        )
        client = _build_client(executor)

        res1 = client.create_order(request=_make_request(order_link_id="link-A"))

        executor._return_response = _make_success_response(
            order_id="order-B", order_link_id="link-B"
        )
        res2 = client.create_order(request=_make_request(order_link_id="link-B"))

        assert res1.order_id == "order-A"
        assert res2.order_id == "order-B"
        assert res1 is not res2

    def test_two_requests_produce_two_payloads(self):
        executor = SpyExecutor()
        client = _build_client(executor)

        client.create_order(request=_make_request(order_link_id="link-1"))
        client.create_order(request=_make_request(order_link_id="link-2"))

        assert executor.calls[0]["payload"]["orderLinkId"] == "link-1"
        assert executor.calls[1]["payload"]["orderLinkId"] == "link-2"

    def test_executor_called_twice_for_two_requests(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request(order_link_id="link-1"))
        client.create_order(request=_make_request(order_link_id="link-2"))
        assert len(executor.calls) == 2

    def test_order_of_calls_preserved(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        client.create_order(request=_make_request(order_link_id="first"))
        client.create_order(request=_make_request(order_link_id="second"))
        assert executor.calls[0]["payload"]["orderLinkId"] == "first"
        assert executor.calls[1]["payload"]["orderLinkId"] == "second"

    def test_no_result_cached_between_calls(self):
        executor = SpyExecutor()
        executor._return_response = _make_success_response(order_id="first-order")
        client = _build_client(executor)

        res1 = client.create_order(request=_make_request(order_link_id="link-1"))

        executor._return_response = _make_success_response(order_id="second-order")
        res2 = client.create_order(request=_make_request(order_link_id="link-2"))

        assert res1.order_id == "first-order"
        assert res2.order_id == "second-order"
        assert res1 is not res2

    def test_order_id_not_mixed_between_calls(self):
        executor = SpyExecutor()
        client = _build_client(executor)

        executor._return_response = _make_success_response(order_id="A")
        res1 = client.create_order(request=_make_request(order_link_id="link-1"))

        executor._return_response = _make_success_response(order_id="B")
        res2 = client.create_order(request=_make_request(order_link_id="link-2"))

        assert res1.order_id == "A"
        assert res2.order_id == "B"

    def test_order_link_id_not_mixed_between_calls(self):
        executor = SpyExecutor()
        client = _build_client(executor)

        executor._return_response = _make_success_response(order_link_id="link-A")
        res1 = client.create_order(request=_make_request(order_link_id="link-1"))

        executor._return_response = _make_success_response(order_link_id="link-B")
        res2 = client.create_order(request=_make_request(order_link_id="link-2"))

        assert res1.order_link_id == "link-A"
        assert res2.order_link_id == "link-B"


# ---------------------------------------------------------------------------
# 6. Ausencia de efectos externos
# ---------------------------------------------------------------------------

class TestNoExternalEffects:
    def test_no_network_calls_on_success(self):
        import socket
        calls = []
        original = socket.socket.connect

        def patched(self, *args, **kwargs):
            calls.append(args)
            return original(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            executor = SpyExecutor()
            client = _build_client(executor)
            client.create_order(request=_make_request())
        finally:
            socket.socket.connect = original

        assert calls == []

    def test_no_env_vars_read(self, monkeypatch):
        monkeypatch.setenv("BYBIT_API_KEY", "integration-test-sentinel")
        monkeypatch.setenv("BYBIT_API_SECRET", "integration-test-secret")
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert isinstance(result, BybitCreateOrderResult)

    def test_no_credentials_required(self):
        executor = SpyExecutor()
        client = _build_client(executor)
        result = client.create_order(request=_make_request())
        assert isinstance(result, BybitCreateOrderResult)

    def test_whole_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        assert GatewayConfig().environment == "demo"


# ===========================================================================
# Sección B — Gateway público: BybitExecutionGateway
# ===========================================================================
#
# Clase concreta del gateway: BybitExecutionGateway
# Método público probado:     execute(request: ExecutionRequest) -> ExecutionResult
#                              (contrato del dominio — Port ExecutionGateway;
#                              ningún tipo Bybit cruza esta frontera pública)
# Frontera simulada:          SpyPrivateApi (reemplaza BybitPrivateApi)
# Componentes reales:         BybitUrlBuilder, BybitEndpointExecutor,
#                             BybitDemoClient, BybitCreateOrderOperation,
#                             BybitCreateOrderPayloadBuilder,
#                             BybitCreateOrderResponseInterpreter
#
# BybitExecutionGateway.execute(ExecutionRequest)
# → traduce a BybitCreateOrderRequest (dentro del adaptador)
# → BybitDemoClient.place_order() → BybitDemoClient.create_order()
# → BybitCreateOrderOperation → BybitCreateOrderPayloadBuilder
# → BybitEndpointExecutor (real) → BybitUrlBuilder (real) → SpyPrivateApi (frontera)
# → BybitResponse → BybitCreateOrderResponseInterpreter → BybitCreateOrderResult
# → traduce a ExecutionResult (dentro del adaptador)
# ===========================================================================

_GATEWAY_BASE_URL = "https://api-demo.bybit.com"


def _make_execution_request(order_id: str = "phoenix-test-order-001", **overrides) -> ExecutionRequest:
    kwargs = dict(
        order_id=order_id,
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity=0.001,
        price=50_000,
    )
    kwargs.update(overrides)
    return ExecutionRequest(**kwargs)


class SpyPrivateApi(BybitPrivateApi):
    """Sustituye BybitPrivateApi — frontera externa más baja."""

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
        return _make_rejected_response()


class ErrorPrivateApi(BybitPrivateApi):
    def __init__(self, error: BaseException):
        self._error = error
        self.call_count = 0

    def request(self, *, url: str, payload: object) -> BybitResponse:
        self.call_count += 1
        raise self._error


def _build_gateway(spy_api: BybitPrivateApi) -> BybitExecutionGateway:
    url_builder = BybitUrlBuilder(base_url=_GATEWAY_BASE_URL)
    real_executor = BybitEndpointExecutor(url_builder=url_builder, private_api=spy_api)
    client = create_bybit_demo_client(endpoint_executor=real_executor)
    return BybitExecutionGateway(client=client)


# ---------------------------------------------------------------------------
# B.1. Diagnóstico — composición del gateway
# ---------------------------------------------------------------------------

class TestGatewayDiagnosis:
    def test_gateway_class_is_bybit_execution_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        assert type(gw) is BybitExecutionGateway

    def test_gateway_has_execute_method(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        assert hasattr(gw, "execute")
        assert callable(gw.execute)

    def test_gateway_contains_bybit_demo_client(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        assert isinstance(gw._client, BybitDemoClient)

    def test_client_contains_real_executor(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        op = gw._client._create_order_operation
        executor = op._endpoint_executor
        assert isinstance(executor, BybitEndpointExecutor)
        assert type(executor) is BybitEndpointExecutor

    def test_spy_is_only_at_private_api_boundary(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        op = gw._client._create_order_operation
        executor = op._endpoint_executor
        assert executor._private_api is spy

    def test_external_boundary_is_private_api(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        op = gw._client._create_order_operation
        executor = op._endpoint_executor
        assert type(executor._private_api) is SpyPrivateApi


# ---------------------------------------------------------------------------
# B.2. Flujo exitoso desde el gateway
# ---------------------------------------------------------------------------

class TestGatewaySuccessFlow:
    def test_gateway_accepts_execution_request(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request())
        assert result is not None

    def test_returns_execution_result(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request())
        assert isinstance(result, ExecutionResult)

    def test_does_not_return_bybit_create_order_result(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request())
        assert not isinstance(result, BybitCreateOrderResult)

    def test_order_id_preserves_domain_identity(self):
        spy = SpyPrivateApi()
        spy._return_response = _make_success_response(order_id="gw-order-456")
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request(order_id="domain-order-1"))
        assert result.order_id == "domain-order-1"

    def test_exchange_order_id_carries_bybit_order_id(self):
        spy = SpyPrivateApi()
        spy._return_response = _make_success_response(order_id="gw-order-456")
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request(order_id="domain-order-1"))
        assert result.exchange_order_id == "gw-order-456"

    def test_payload_order_link_id_uses_domain_order_id(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request(order_id="domain-order-9"))
        assert spy.calls[0]["payload"]["orderLinkId"] == "domain-order-9"

    def test_private_api_called_exactly_once(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert len(spy.calls) == 1

    def test_correct_url_sent_to_boundary(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        expected_url = _GATEWAY_BASE_URL + BYBIT_CREATE_ORDER_ENDPOINT.path
        assert spy.calls[0]["url"] == expected_url

    def test_endpoint_path_in_url(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert "/v5/order/create" in spy.calls[0]["url"]

    def test_payload_category_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["category"] == "linear"

    def test_payload_symbol_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["symbol"] == "BTCUSDT"

    def test_payload_side_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["side"] == "Buy"

    def test_payload_order_type_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["orderType"] == "Limit"

    def test_payload_qty_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["qty"] == "0.001"

    def test_payload_price_at_gateway(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert spy.calls[0]["payload"]["price"] == "50000"

    def test_does_not_return_bybit_response(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        result = gw.execute(_make_execution_request())
        assert not isinstance(result, BybitResponse)

    def test_no_retry_on_success(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request())
        assert len(spy.calls) == 1

    def test_no_network_calls(self):
        import socket
        network_calls = []
        original_connect = socket.socket.connect

        def patched(self, *args, **kwargs):
            network_calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched
        try:
            spy = SpyPrivateApi()
            gw = _build_gateway(spy)
            gw.execute(_make_execution_request())
        finally:
            socket.socket.connect = original_connect

        assert network_calls == []


# ---------------------------------------------------------------------------
# B.3. Rechazo de API desde el gateway
# ---------------------------------------------------------------------------

class TestGatewayApiRejection:
    def test_rejection_does_not_raise_bybit_api_error(self):
        gw = _build_gateway(RejectingPrivateApi())
        try:
            gw.execute(_make_execution_request())
        except BybitApiError:
            pytest.fail("BybitApiError must not cross the ExecutionGateway boundary")

    def test_rejection_returns_execution_result(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request())
        assert isinstance(result, ExecutionResult)

    def test_rejection_status_is_rejected(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request())
        assert result.status == "rejected"

    def test_rejection_error_message_carries_ret_msg(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request())
        assert result.error_message == "Request parameter error"

    def test_rejection_preserves_domain_order_id(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request(order_id="domain-77"))
        assert result.order_id == "domain-77"

    def test_rejection_has_no_exchange_order_id(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request())
        assert result.exchange_order_id is None

    def test_boundary_called_exactly_once_on_rejection(self):
        api = RejectingPrivateApi()
        gw = _build_gateway(api)
        gw.execute(_make_execution_request())
        assert api.call_count == 1

    def test_no_retry_on_rejection(self):
        api = RejectingPrivateApi()
        gw = _build_gateway(api)
        gw.execute(_make_execution_request())
        assert api.call_count == 1

    def test_does_not_return_create_order_result(self):
        gw = _build_gateway(RejectingPrivateApi())
        result = gw.execute(_make_execution_request())
        assert not isinstance(result, BybitCreateOrderResult)


# ---------------------------------------------------------------------------
# B.4. Error de infraestructura desde el gateway
# ---------------------------------------------------------------------------

class TestGatewayInfrastructureError:
    def test_exception_translated_to_execution_infrastructure_error(self):
        transport_error = RuntimeError("simulated transport failure")
        gw = _build_gateway(ErrorPrivateApi(transport_error))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_execution_request())

    def test_original_exception_conserved_as_cause(self):
        transport_error = RuntimeError("simulated transport failure")
        gw = _build_gateway(ErrorPrivateApi(transport_error))
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_execution_request())
        assert exc_info.value.__cause__ is transport_error

    def test_message_conserved(self):
        gw = _build_gateway(ErrorPrivateApi(RuntimeError("raw error")))
        with pytest.raises(ExecutionInfrastructureError) as exc_info:
            gw.execute(_make_execution_request())
        assert str(exc_info.value) == "raw error"

    def test_exception_not_transformed_to_bybit_api_error(self):
        gw = _build_gateway(ErrorPrivateApi(RuntimeError("raw error")))
        with pytest.raises(ExecutionInfrastructureError):
            try:
                gw.execute(_make_execution_request())
            except BybitApiError:
                pytest.fail("RuntimeError must not be converted to BybitApiError")

    def test_boundary_called_exactly_once_on_error(self):
        api = ErrorPrivateApi(OSError("connection refused"))
        gw = _build_gateway(api)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_execution_request())
        assert api.call_count == 1

    def test_no_retry_on_transport_error(self):
        api = ErrorPrivateApi(RuntimeError("fail"))
        gw = _build_gateway(api)
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_execution_request())
        assert api.call_count == 1

    def test_interpreter_not_called_on_transport_error(self, monkeypatch):
        calls = []
        original = BybitCreateOrderResponseInterpreter.interpret
        monkeypatch.setattr(
            BybitCreateOrderResponseInterpreter,
            "interpret",
            lambda self, *, response: calls.append(response) or original(self, response=response),
        )
        gw = _build_gateway(ErrorPrivateApi(RuntimeError("fail")))
        with pytest.raises(ExecutionInfrastructureError):
            gw.execute(_make_execution_request())
        assert calls == []


# ---------------------------------------------------------------------------
# B.5. Múltiples llamadas desde el gateway
# ---------------------------------------------------------------------------

class TestGatewayMultipleCalls:
    def test_two_requests_produce_distinct_results(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)

        spy._return_response = _make_success_response(order_id="A")
        res1 = gw.execute(_make_execution_request(order_id="domain-1"))

        spy._return_response = _make_success_response(order_id="B")
        res2 = gw.execute(_make_execution_request(order_id="domain-2"))

        assert res1.exchange_order_id == "A"
        assert res2.exchange_order_id == "B"
        assert res1 is not res2

    def test_two_requests_produce_two_payloads(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request(order_id="first"))
        gw.execute(_make_execution_request(order_id="second"))
        assert spy.calls[0]["payload"]["orderLinkId"] == "first"
        assert spy.calls[1]["payload"]["orderLinkId"] == "second"

    def test_boundary_called_twice_for_two_requests(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request(order_id="l1"))
        gw.execute(_make_execution_request(order_id="l2"))
        assert len(spy.calls) == 2

    def test_order_of_calls_preserved(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        gw.execute(_make_execution_request(order_id="first"))
        gw.execute(_make_execution_request(order_id="second"))
        assert spy.calls[0]["payload"]["orderLinkId"] == "first"
        assert spy.calls[1]["payload"]["orderLinkId"] == "second"

    def test_no_result_cached_between_calls(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)

        spy._return_response = _make_success_response(order_id="first-order")
        res1 = gw.execute(_make_execution_request(order_id="l1"))

        spy._return_response = _make_success_response(order_id="second-order")
        res2 = gw.execute(_make_execution_request(order_id="l2"))

        assert res1.exchange_order_id == "first-order"
        assert res2.exchange_order_id == "second-order"
        assert res1 is not res2

    def test_order_id_not_mixed(self):
        spy = SpyPrivateApi()
        gw = _build_gateway(spy)
        spy._return_response = _make_success_response(order_id="X")
        r1 = gw.execute(_make_execution_request(order_id="l1"))
        spy._return_response = _make_success_response(order_id="Y")
        r2 = gw.execute(_make_execution_request(order_id="l2"))
        assert r1.exchange_order_id == "X"
        assert r2.exchange_order_id == "Y"
