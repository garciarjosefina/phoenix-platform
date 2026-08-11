import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT
from execution_gateway.bybit_open_orders_reader import BybitOpenOrdersReader
from execution_gateway.bybit_open_orders_response_interpreter import BybitOpenOrdersResponseInterpreter
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot

_SENTINEL_URL = "https://api-demo.bybit.com/v5/order/realtime"
_SENTINEL_RESPONSE = BybitResponse(
    ret_code=0, ret_msg="OK", result={"category": "linear", "list": ()}, ret_ext_info={}, time_ms=1_000,
)
_SENTINEL_SNAPSHOT = OpenOrdersSnapshot(orders=(), server_time_ms=1_000)


class _SpyUrlBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyPrivateGetApi(BybitPrivateGetApi):
    def __init__(
        self,
        *,
        result: BybitResponse | None = None,
        results: list[BybitResponse] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._results = list(results) if results is not None else None
        self._result = result if result is not None else _SENTINEL_RESPONSE
        self._exc = exc

    def request(self, *, url: str, query_string: str) -> BybitResponse:
        self.calls.append({"url": url, "query_string": query_string})
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


class _SpyInterpreter(BybitOpenOrdersResponseInterpreter):
    def __init__(
        self,
        *,
        result: OpenOrdersSnapshot | None = None,
        results: list[OpenOrdersSnapshot] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._results = list(results) if results is not None else None
        self._result = result if result is not None else _SENTINEL_SNAPSHOT
        self._exc = exc

    def interpret(self, *, response: BybitResponse) -> OpenOrdersSnapshot:
        self.calls.append({"response": response})
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


def _reader(*, url_builder=None, private_get_api=None, response_interpreter=None):
    return BybitOpenOrdersReader(
        private_get_api=private_get_api or _SpyPrivateGetApi(),
        url_builder=url_builder or _SpyUrlBuilder(),
        response_interpreter=response_interpreter or _SpyInterpreter(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitOpenOrdersReader")
        assert execution_gateway.BybitOpenOrdersReader is BybitOpenOrdersReader

    def test_in_all(self):
        assert "BybitOpenOrdersReader" in execution_gateway.__all__

    def test_satisfies_open_orders_reader_protocol(self):
        from execution_gateway.open_orders_reader import OpenOrdersReader
        assert isinstance(_reader(), OpenOrdersReader)


class TestConstruction:
    def test_private_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetApi"):
            BybitOpenOrdersReader(
                private_get_api=object(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_url_builder_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitUrlBuilder"):
            BybitOpenOrdersReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=object(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_response_interpreter_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitOpenOrdersResponseInterpreter"):
            BybitOpenOrdersReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=object(),
            )


class TestQueryOpenOrders:
    def test_returns_open_orders_snapshot(self):
        snapshot = _reader().query_open_orders()
        assert isinstance(snapshot, OpenOrdersSnapshot)

    def test_returns_interpreter_result_by_identity(self):
        interpreter = _SpyInterpreter(result=_SENTINEL_SNAPSHOT)
        reader = _reader(response_interpreter=interpreter)
        assert reader.query_open_orders() is _SENTINEL_SNAPSHOT

    def test_url_built_from_open_orders_endpoint(self):
        url_builder = _SpyUrlBuilder()
        reader = _reader(url_builder=url_builder)
        reader.query_open_orders()
        assert url_builder.calls[0]["endpoint"] is BYBIT_OPEN_ORDERS_ENDPOINT

    def test_uses_url_from_builder(self):
        api = _SpyPrivateGetApi()
        reader = _reader(url_builder=_SpyUrlBuilder(result="https://custom/x"), private_get_api=api)
        reader.query_open_orders()
        assert api.calls[0]["url"] == "https://custom/x"

    def test_scope_fixed_to_linear(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_open_orders()
        assert "category=linear" in api.calls[0]["query_string"]

    def test_query_string_includes_settle_coin(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_open_orders()
        assert "settleCoin=USDT" in api.calls[0]["query_string"]

    def test_response_passed_to_interpreter_by_identity(self):
        response = BybitResponse(ret_code=0, ret_msg="OK", result={"list": ()}, ret_ext_info={}, time_ms=1)
        interpreter = _SpyInterpreter()
        reader = _reader(
            private_get_api=_SpyPrivateGetApi(result=response),
            response_interpreter=interpreter,
        )
        reader.query_open_orders()
        assert interpreter.calls[0]["response"] is response

    def test_exactly_one_api_request_call(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_open_orders()
        assert len(api.calls) == 1

    def test_exactly_one_interpret_call(self):
        interpreter = _SpyInterpreter()
        reader = _reader(response_interpreter=interpreter)
        reader.query_open_orders()
        assert len(interpreter.calls) == 1


class TestErrorTranslation:
    """Ningún tipo Bybit cruza query_open_orders() -- mismo principio que
    BybitPositionsReader/bybit_gateway.py: todo se traduce a
    ExecutionInfrastructureError ya existente, sin inventar jerarquía nueva."""

    def test_api_error_translated_to_infrastructure_error(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_open_orders()

    def test_bybit_api_error_does_not_cross_the_port(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_open_orders()
            assert False, "expected ExecutionInfrastructureError"
        except BybitApiError:
            assert False, "BybitApiError must not cross the read Port"
        except ExecutionInfrastructureError:
            pass

    def test_response_processing_error_from_interpreter_translated(self):
        interpreter = _SpyInterpreter(exc=BybitResponseProcessingError(message="bad schema"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_open_orders()

    def test_response_processing_error_from_transport_layer_translated(self):
        api = _SpyPrivateGetApi(exc=BybitResponseProcessingError(message="bad utf-8"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_open_orders()

    def test_os_error_from_transport_translated(self):
        api = _SpyPrivateGetApi(exc=OSError("connection refused"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_open_orders()

    def test_original_error_preserved_as_cause(self):
        original = BybitApiError(ret_code=10003, ret_msg="invalid key")
        interpreter = _SpyInterpreter(exc=original)
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_open_orders()
        except ExecutionInfrastructureError as error:
            assert error.__cause__ is original

    def test_infrastructure_error_message_does_not_leak_ret_msg(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="SUPER_SECRET_DETAIL"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_open_orders()
            assert False
        except ExecutionInfrastructureError as error:
            assert "SUPER_SECRET_DETAIL" not in str(error)

    def test_type_error_from_interpreter_propagates_unwrapped(self):
        interpreter = _SpyInterpreter(exc=TypeError("programming bug"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(TypeError, match="programming bug"):
            reader.query_open_orders()


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.bybit_open_orders_reader as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "BybitCreateOrderOperation" not in src
        assert "/v5/order/create" not in src

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.bybit_open_orders_reader as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")


class TestNoCacheAcrossCalls:
    """Lección directa del Hito 3.70 (IMPORTANT-3): la garantía de ausencia
    de caché se prueba desde el primer commit, no se agrega después de una
    auditoría. Un futuro Reconciliation Engine mantendrá vivo un mismo
    BybitOpenOrdersReader y lo consultará repetidas veces."""

    def test_api_called_exactly_twice_on_two_queries(self):
        api = _SpyPrivateGetApi(results=[_SENTINEL_RESPONSE, _SENTINEL_RESPONSE])
        reader = _reader(private_get_api=api)
        reader.query_open_orders()
        reader.query_open_orders()
        assert len(api.calls) == 2

    def test_interpreter_called_exactly_twice_on_two_queries(self):
        snap_a = OpenOrdersSnapshot(orders=(), server_time_ms=1)
        snap_b = OpenOrdersSnapshot(orders=(), server_time_ms=2)
        interpreter = _SpyInterpreter(results=[snap_a, snap_b])
        reader = _reader(response_interpreter=interpreter)
        reader.query_open_orders()
        reader.query_open_orders()
        assert len(interpreter.calls) == 2

    def test_two_calls_on_same_instance_return_distinct_snapshots_by_identity(self):
        snap_a = OpenOrdersSnapshot(orders=(), server_time_ms=1)
        snap_b = OpenOrdersSnapshot(orders=(), server_time_ms=2)
        interpreter = _SpyInterpreter(results=[snap_a, snap_b])
        reader = _reader(response_interpreter=interpreter)
        first = reader.query_open_orders()
        second = reader.query_open_orders()
        assert first is snap_a
        assert second is snap_b
        assert first is not second

    def test_second_snapshot_reflects_second_api_response_end_to_end(self):
        resp1 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"category": "linear", "list": ()}, ret_ext_info={}, time_ms=111,
        )
        resp2 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"category": "linear", "list": ()}, ret_ext_info={}, time_ms=222,
        )
        api = _SpyPrivateGetApi(results=[resp1, resp2])
        reader = _reader(private_get_api=api, response_interpreter=BybitOpenOrdersResponseInterpreter())
        first = reader.query_open_orders()
        second = reader.query_open_orders()
        assert first.server_time_ms == 111
        assert second.server_time_ms == 222

    def test_reader_instance_has_no_cache_attribute_after_query(self):
        reader = _reader()
        reader.query_open_orders()
        assert not hasattr(reader, "_cached")
        assert not hasattr(reader, "_cache")
        assert not hasattr(reader, "_last_result")
        assert not hasattr(reader, "_last_snapshot")

    def test_two_independent_reader_instances_do_not_share_state(self):
        reader_a = _reader()
        reader_b = _reader()
        assert reader_a is not reader_b
        assert vars(reader_a).keys() == {"_private_get_api", "_url_builder", "_response_interpreter"}

    def test_second_query_after_first_failure_still_calls_api_again(self):
        api = _SpyPrivateGetApi(exc=OSError("down"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_open_orders()
        api._exc = None
        api._result = _SENTINEL_RESPONSE
        reader.query_open_orders()
        assert len(api.calls) == 2
