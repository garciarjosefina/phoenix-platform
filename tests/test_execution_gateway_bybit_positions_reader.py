import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_endpoints import BYBIT_POSITIONS_ENDPOINT
from execution_gateway.bybit_positions_reader import BybitPositionsReader
from execution_gateway.bybit_positions_response_interpreter import BybitPositionsResponseInterpreter
from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.positions_contracts import PositionsSnapshot

_SENTINEL_URL = "https://api-demo.bybit.com/v5/position/list"
_SENTINEL_RESPONSE = BybitResponse(
    ret_code=0, ret_msg="OK", result={"category": "linear", "list": ()}, ret_ext_info={}, time_ms=1_000,
)
_SENTINEL_SNAPSHOT = PositionsSnapshot(positions=(), server_time_ms=1_000)


class _SpyUrlBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyPrivateGetApi(BybitPrivateGetApi):
    def __init__(self, *, result: BybitResponse | None = None, exc: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _SENTINEL_RESPONSE
        self._exc = exc

    def request(self, *, url: str, query_string: str) -> BybitResponse:
        self.calls.append({"url": url, "query_string": query_string})
        if self._exc is not None:
            raise self._exc
        return self._result


class _SpyInterpreter(BybitPositionsResponseInterpreter):
    def __init__(self, *, result: PositionsSnapshot | None = None, exc: Exception | None = None) -> None:
        self.calls: list[dict] = []
        self._result = result if result is not None else _SENTINEL_SNAPSHOT
        self._exc = exc

    def interpret(self, *, response: BybitResponse) -> PositionsSnapshot:
        self.calls.append({"response": response})
        if self._exc is not None:
            raise self._exc
        return self._result


def _reader(*, url_builder=None, private_get_api=None, response_interpreter=None):
    return BybitPositionsReader(
        private_get_api=private_get_api or _SpyPrivateGetApi(),
        url_builder=url_builder or _SpyUrlBuilder(),
        response_interpreter=response_interpreter or _SpyInterpreter(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPositionsReader")
        assert execution_gateway.BybitPositionsReader is BybitPositionsReader

    def test_in_all(self):
        assert "BybitPositionsReader" in execution_gateway.__all__

    def test_satisfies_positions_reader_protocol(self):
        from execution_gateway.positions_reader import PositionsReader
        assert isinstance(_reader(), PositionsReader)


class TestConstruction:
    def test_private_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPrivateGetApi"):
            BybitPositionsReader(
                private_get_api=object(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_url_builder_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitUrlBuilder"):
            BybitPositionsReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=object(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_response_interpreter_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPositionsResponseInterpreter"):
            BybitPositionsReader(
                private_get_api=_SpyPrivateGetApi(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=object(),
            )


class TestQueryPositions:
    def test_returns_positions_snapshot(self):
        snapshot = _reader().query_positions()
        assert isinstance(snapshot, PositionsSnapshot)

    def test_returns_interpreter_result_by_identity(self):
        interpreter = _SpyInterpreter(result=_SENTINEL_SNAPSHOT)
        reader = _reader(response_interpreter=interpreter)
        assert reader.query_positions() is _SENTINEL_SNAPSHOT

    def test_url_built_from_positions_endpoint(self):
        url_builder = _SpyUrlBuilder()
        reader = _reader(url_builder=url_builder)
        reader.query_positions()
        assert url_builder.calls[0]["endpoint"] is BYBIT_POSITIONS_ENDPOINT

    def test_uses_url_from_builder(self):
        api = _SpyPrivateGetApi()
        reader = _reader(url_builder=_SpyUrlBuilder(result="https://custom/x"), private_get_api=api)
        reader.query_positions()
        assert api.calls[0]["url"] == "https://custom/x"

    def test_scope_fixed_to_linear(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_positions()
        assert "category=linear" in api.calls[0]["query_string"]

    def test_query_string_includes_settle_coin(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_positions()
        assert "settleCoin=USDT" in api.calls[0]["query_string"]

    def test_response_passed_to_interpreter_by_identity(self):
        response = BybitResponse(ret_code=0, ret_msg="OK", result={"list": ()}, ret_ext_info={}, time_ms=1)
        interpreter = _SpyInterpreter()
        reader = _reader(
            private_get_api=_SpyPrivateGetApi(result=response),
            response_interpreter=interpreter,
        )
        reader.query_positions()
        assert interpreter.calls[0]["response"] is response

    def test_exactly_one_api_request_call(self):
        api = _SpyPrivateGetApi()
        reader = _reader(private_get_api=api)
        reader.query_positions()
        assert len(api.calls) == 1

    def test_exactly_one_interpret_call(self):
        interpreter = _SpyInterpreter()
        reader = _reader(response_interpreter=interpreter)
        reader.query_positions()
        assert len(interpreter.calls) == 1


class TestErrorTranslation:
    """Ningún tipo Bybit cruza query_positions() -- mismo principio que
    bybit_gateway.py (ADR-001A): todo se traduce a ExecutionInfrastructureError,
    ya existente, sin inventar una jerarquía nueva."""

    def test_api_error_translated_to_infrastructure_error(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_positions()

    def test_bybit_api_error_does_not_cross_the_port(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="invalid key"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_positions()
            assert False, "expected ExecutionInfrastructureError"
        except BybitApiError:
            assert False, "BybitApiError must not cross the read Port"
        except ExecutionInfrastructureError:
            pass

    def test_response_processing_error_from_interpreter_translated(self):
        interpreter = _SpyInterpreter(exc=BybitResponseProcessingError(message="bad schema"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_positions()

    def test_response_processing_error_from_transport_layer_translated(self):
        api = _SpyPrivateGetApi(exc=BybitResponseProcessingError(message="bad utf-8"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_positions()

    def test_os_error_from_transport_translated(self):
        api = _SpyPrivateGetApi(exc=OSError("connection refused"))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_positions()

    def test_http_error_translated(self):
        import urllib.error
        api = _SpyPrivateGetApi(exc=urllib.error.HTTPError("url", 403, "Forbidden", {}, None))
        reader = _reader(private_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_positions()

    def test_original_error_preserved_as_cause(self):
        original = BybitApiError(ret_code=10003, ret_msg="invalid key")
        interpreter = _SpyInterpreter(exc=original)
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_positions()
        except ExecutionInfrastructureError as error:
            assert error.__cause__ is original

    def test_infrastructure_error_message_does_not_leak_ret_msg(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10003, ret_msg="SUPER_SECRET_DETAIL"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_positions()
            assert False
        except ExecutionInfrastructureError as error:
            assert "SUPER_SECRET_DETAIL" not in str(error)

    def test_type_error_from_interpreter_propagates_unwrapped(self):
        interpreter = _SpyInterpreter(exc=TypeError("programming bug"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(TypeError, match="programming bug"):
            reader.query_positions()


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.bybit_positions_reader as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "BybitCreateOrderOperation" not in src
        assert "/v5/order/create" not in src

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.bybit_positions_reader as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")
