import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_endpoints import BYBIT_OPEN_ORDERS_ENDPOINT
from execution_gateway.bybit_order_realtime_lookup import BybitOrderRealtimeLookup
from execution_gateway.bybit_order_realtime_response_interpreter import (
    BybitOrderRealtimeResponseInterpreter,
)
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderNotFound
from execution_gateway.order_realtime_lookup_reader import OrderRealtimeLookupReader

_OID = ExecutionOrderId(value="ord_" + "a" * 32)
_SENTINEL_URL = "https://api-demo.bybit.com/v5/order/realtime"
_SENTINEL_RESPONSE = BybitResponse(
    ret_code=0, ret_msg="OK", result={"category": "linear", "list": ()}, ret_ext_info={}, time_ms=1_000,
)
_SENTINEL_RESULT = BybitRealtimeOrderNotFound()


class _SpyUrlBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyPrivateGetApi(BybitPrivateGetApi):
    def __init__(self, *, result=None, exc=None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _SENTINEL_RESPONSE
        self._exc = exc

    def request(self, *, url: str, query_string: str) -> BybitResponse:
        self.calls.append({"url": url, "query_string": query_string})
        if self._exc is not None:
            raise self._exc
        return self._result


class _SpyInterpreter(BybitOrderRealtimeResponseInterpreter):
    def __init__(self, *, result=None, exc=None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _SENTINEL_RESULT
        self._exc = exc

    def interpret(self, *, response: BybitResponse, execution_order_id: ExecutionOrderId):
        self.calls.append({"response": response, "execution_order_id": execution_order_id})
        if self._exc is not None:
            raise self._exc
        return self._result


def _lookup(*, url_builder=None, private_get_api=None, response_interpreter=None):
    return BybitOrderRealtimeLookup(
        private_get_api=private_get_api or _SpyPrivateGetApi(),
        url_builder=url_builder or _SpyUrlBuilder(),
        response_interpreter=response_interpreter or _SpyInterpreter(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitOrderRealtimeLookup")
        assert execution_gateway.BybitOrderRealtimeLookup is BybitOrderRealtimeLookup

    def test_in_all(self):
        assert "BybitOrderRealtimeLookup" in execution_gateway.__all__

    def test_satisfies_order_realtime_lookup_reader_protocol(self):
        assert isinstance(_lookup(), OrderRealtimeLookupReader)


class TestConstruction:
    def test_private_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetApi"):
            BybitOrderRealtimeLookup(
                private_get_api=object(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_url_builder_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitUrlBuilder"):
            BybitOrderRealtimeLookup(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=object(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_response_interpreter_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitOrderRealtimeResponseInterpreter"):
            BybitOrderRealtimeLookup(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=object(),
            )


class TestLookupInputValidation:
    def test_rejects_raw_string_identity(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            _lookup().lookup_by_execution_order_id(execution_order_id="ord_" + "a" * 32)

    def test_rejects_none_identity(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            _lookup().lookup_by_execution_order_id(execution_order_id=None)


class TestQuery:
    def test_url_built_from_open_orders_endpoint(self):
        # Reutiliza el endpoint YA ACEPTADO en el Hito 3.71
        # (BYBIT_OPEN_ORDERS_ENDPOINT = /v5/order/realtime) -- no se crea
        # una constante nueva.
        url_builder = _SpyUrlBuilder()
        lookup = _lookup(url_builder=url_builder)
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        assert url_builder.calls[0]["endpoint"] is BYBIT_OPEN_ORDERS_ENDPOINT

    def test_endpoint_path_is_realtime_not_history(self):
        assert BYBIT_OPEN_ORDERS_ENDPOINT.path == "/v5/order/realtime"
        assert BYBIT_OPEN_ORDERS_ENDPOINT.method == "GET"

    def test_uses_url_from_builder(self):
        api = _SpyPrivateGetApi()
        lookup = _lookup(url_builder=_SpyUrlBuilder(result="https://custom/x"), private_get_api=api)
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        assert api.calls[0]["url"] == "https://custom/x"

    def test_scope_fixed_to_linear(self):
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert "category=linear" in api.calls[0]["query_string"]

    def test_query_string_is_exactly_category_and_order_link_id(self):
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert api.calls[0]["query_string"] == f"category=linear&orderLinkId={_OID.value}"

    def test_query_string_never_includes_open_only(self):
        # Documentación oficial: openOnly se IGNORA al filtrar por
        # orderLinkId -- incluirlo comunicaría una garantía inexistente.
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert "openOnly" not in api.calls[0]["query_string"]

    def test_query_string_never_includes_symbol_filter(self):
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert "symbol=" not in api.calls[0]["query_string"]

    def test_query_string_never_includes_order_id_filter(self):
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert "&orderId=" not in api.calls[0]["query_string"]
        assert not api.calls[0]["query_string"].startswith("orderId=")

    def test_response_passed_to_interpreter_by_identity(self):
        response = BybitResponse(ret_code=0, ret_msg="OK", result={"list": ()}, ret_ext_info={}, time_ms=1)
        interpreter = _SpyInterpreter()
        lookup = _lookup(
            private_get_api=_SpyPrivateGetApi(result=response),
            response_interpreter=interpreter,
        )
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        assert interpreter.calls[0]["response"] is response

    def test_execution_order_id_passed_to_interpreter_by_identity(self):
        interpreter = _SpyInterpreter()
        _lookup(response_interpreter=interpreter).lookup_by_execution_order_id(execution_order_id=_OID)
        assert interpreter.calls[0]["execution_order_id"] is _OID

    def test_exactly_one_api_request_call(self):
        api = _SpyPrivateGetApi()
        _lookup(private_get_api=api).lookup_by_execution_order_id(execution_order_id=_OID)
        assert len(api.calls) == 1

    def test_returns_interpreter_result_by_identity(self):
        interpreter = _SpyInterpreter(result=_SENTINEL_RESULT)
        lookup = _lookup(response_interpreter=interpreter)
        assert lookup.lookup_by_execution_order_id(execution_order_id=_OID) is _SENTINEL_RESULT


class TestErrorTranslation:
    def test_api_error_translated_to_infrastructure_error(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        lookup = _lookup(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)

    def test_bybit_api_error_does_not_cross_the_port(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        lookup = _lookup(response_interpreter=interpreter)
        try:
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)
            assert False, "expected ExecutionInfrastructureError"
        except BybitApiError:
            assert False, "BybitApiError must not cross the read Port"
        except ExecutionInfrastructureError:
            pass

    def test_response_processing_error_from_interpreter_translated(self):
        interpreter = _SpyInterpreter(exc=BybitResponseProcessingError(message="bad schema"))
        lookup = _lookup(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)

    def test_os_error_from_transport_translated(self):
        api = _SpyPrivateGetApi(exc=OSError("connection refused"))
        lookup = _lookup(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)

    def test_original_error_preserved_as_cause(self):
        original = BybitApiError(ret_code=10003, ret_msg="invalid key")
        interpreter = _SpyInterpreter(exc=original)
        lookup = _lookup(response_interpreter=interpreter)
        try:
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        except ExecutionInfrastructureError as error:
            assert error.__cause__ is original

    def test_infrastructure_error_message_does_not_leak_ret_msg(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="SUPER_SECRET_DETAIL"))
        lookup = _lookup(response_interpreter=interpreter)
        try:
            lookup.lookup_by_execution_order_id(execution_order_id=_OID)
            assert False
        except ExecutionInfrastructureError as error:
            assert "SUPER_SECRET_DETAIL" not in str(error)

    def test_not_found_never_becomes_an_error(self):
        interpreter = _SpyInterpreter(result=BybitRealtimeOrderNotFound())
        result = _lookup(response_interpreter=interpreter).lookup_by_execution_order_id(
            execution_order_id=_OID
        )
        assert isinstance(result, BybitRealtimeOrderNotFound)


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.bybit_order_realtime_lookup as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "/v5/order/create" not in src

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.bybit_order_realtime_lookup as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")

    def test_does_not_import_ledger_event_contracts(self):
        import execution_gateway.bybit_order_realtime_lookup as module
        assert not hasattr(module, "OrderObservedClosed")
        assert not hasattr(module, "OrderObservedOpen")
        assert not hasattr(module, "ExecutionLedgerEvent")
        assert not hasattr(module, "OrderIdentityReportedDuplicateByExchange")


class TestNoRecoveryOr110072:
    def test_module_imports_nothing_from_writer_postgres_or_110072(self):
        import execution_gateway.bybit_order_realtime_lookup as module
        assert "psycopg" not in vars(module)
        assert not hasattr(module, "ExecutionLedgerWriter")
        assert not hasattr(module, "AppendReceipt")

    def test_lookup_makes_no_retry_or_loop(self):
        import ast
        import inspect
        import execution_gateway.bybit_order_realtime_lookup as module
        tree = ast.parse(inspect.getsource(module))
        method = next(
            node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "lookup_by_execution_order_id"
        )
        loop_nodes = [n for n in ast.walk(method) if isinstance(n, (ast.For, ast.While))]
        assert loop_nodes == []


class TestNoCacheAcrossCalls:
    def test_api_called_exactly_twice_on_two_lookups(self):
        api = _SpyPrivateGetApi()
        lookup = _lookup(private_get_api=api)
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        assert len(api.calls) == 2

    def test_lookup_instance_has_no_cache_attribute(self):
        lookup = _lookup()
        lookup.lookup_by_execution_order_id(execution_order_id=_OID)
        assert not hasattr(lookup, "_cache")
        assert not hasattr(lookup, "_last_result")

    def test_two_independent_instances_do_not_share_state(self):
        a = _lookup()
        b = _lookup()
        assert vars(a).keys() == {"_private_get_api", "_url_builder", "_response_interpreter"}
        assert a is not b
