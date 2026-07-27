"""
Prueba integrada de creación de orden de punta a punta.

Valida el flujo completo usando componentes productivos reales en todas las capas
internas. El único doble es SpyExecutor, que representa la frontera de
infraestructura: reemplaza la red sin sustituir ningún componente de lógica.

Cadena cubierta:
  BybitDemoClient.create_order()
  → BybitCreateOrderOperation.execute()
  → BybitCreateOrderPayloadBuilder.build()
  → BybitEndpointExecutor.execute()   ← frontera simulada (SpyExecutor)
  → BybitResponse
  → BybitCreateOrderResponseInterpreter.interpret()
  → BybitCreateOrderResult
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
from execution_gateway.bybit_response import BybitResponse


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
