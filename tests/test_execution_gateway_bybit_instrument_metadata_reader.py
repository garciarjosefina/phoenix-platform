from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_endpoint import BybitEndpoint
from execution_gateway.bybit_endpoints import BYBIT_INSTRUMENTS_INFO_ENDPOINT
from execution_gateway.bybit_instrument_metadata_reader import BybitInstrumentMetadataReader
from execution_gateway.bybit_instrument_metadata_response_interpreter import (
    BybitInstrumentMetadataResponseInterpreter,
)
from execution_gateway.bybit_public_get_api import BybitPublicGetApi
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.execution_infrastructure_error import ExecutionInfrastructureError
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata

_SENTINEL_URL = "https://api-demo.bybit.com/v5/market/instruments-info"
_SENTINEL_ITEM = {
    "symbol": "BTCUSDT", "contractType": "LinearPerpetual", "status": "Trading",
    "baseCoin": "BTC", "quoteCoin": "USDT", "settleCoin": "USDT",
    "priceFilter": {"minPrice": "0.10", "maxPrice": "1999999.80", "tickSize": "0.10"},
    "lotSizeFilter": {"maxOrderQty": "1190.000", "minOrderQty": "0.001", "qtyStep": "0.001"},
}
_SENTINEL_RESPONSE = BybitResponse(
    ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ITEM,), "nextPageCursor": ""},
    ret_ext_info={}, time_ms=1_000,
)
_SENTINEL_METADATA = ExecutionInstrumentMetadata(
    symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
    instrument_status="Trading", contract_type="LinearPerpetual",
    tick_size=Decimal("0.10"), min_price=Decimal("0.10"), max_price=Decimal("1999999.80"),
    qty_step=Decimal("0.001"), min_order_qty=Decimal("0.001"), max_order_qty=Decimal("1190.000"),
    server_time_ms=1_000,
)


class _SpyUrlBuilder(BybitUrlBuilder):
    def __init__(self, result: str = _SENTINEL_URL) -> None:
        self.calls: list[dict] = []
        self._result = result

    def build(self, *, endpoint: BybitEndpoint) -> str:
        self.calls.append({"endpoint": endpoint})
        return self._result


class _SpyPublicGetApi(BybitPublicGetApi):
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


class _SpyInterpreter(BybitInstrumentMetadataResponseInterpreter):
    def __init__(
        self,
        *,
        result: ExecutionInstrumentMetadata | None = None,
        results: list[ExecutionInstrumentMetadata] | None = None,
        exc: Exception | None = None,
    ) -> None:
        self.calls: list[dict] = []
        self._results = list(results) if results is not None else None
        self._result = result if result is not None else _SENTINEL_METADATA
        self._exc = exc

    def interpret(self, *, response: BybitResponse, requested_symbol: str) -> ExecutionInstrumentMetadata:
        self.calls.append({"response": response, "requested_symbol": requested_symbol})
        if self._exc is not None:
            raise self._exc
        if self._results is not None:
            return self._results.pop(0)
        return self._result


def _reader(*, url_builder=None, public_get_api=None, response_interpreter=None):
    return BybitInstrumentMetadataReader(
        public_get_api=public_get_api or _SpyPublicGetApi(),
        url_builder=url_builder or _SpyUrlBuilder(),
        response_interpreter=response_interpreter or _SpyInterpreter(),
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitInstrumentMetadataReader")
        assert execution_gateway.BybitInstrumentMetadataReader is BybitInstrumentMetadataReader

    def test_in_all(self):
        assert "BybitInstrumentMetadataReader" in execution_gateway.__all__

    def test_satisfies_instrument_metadata_reader_protocol(self):
        from execution_gateway.instrument_metadata_reader import InstrumentMetadataReader
        assert isinstance(_reader(), InstrumentMetadataReader)


class TestConstruction:
    def test_public_get_api_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitPublicGetApi"):
            BybitInstrumentMetadataReader(
                public_get_api=object(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_url_builder_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitUrlBuilder"):
            BybitInstrumentMetadataReader(
                public_get_api=_SpyPublicGetApi(),
                url_builder=object(),
                response_interpreter=_SpyInterpreter(),
            )

    def test_response_interpreter_must_be_correct_type(self):
        with pytest.raises(TypeError, match="BybitInstrumentMetadataResponseInterpreter"):
            BybitInstrumentMetadataReader(
                public_get_api=_SpyPublicGetApi(),
                url_builder=_SpyUrlBuilder(),
                response_interpreter=object(),
            )


class TestSymbolInputValidation:
    def test_symbol_must_be_str(self):
        reader = _reader()
        with pytest.raises(TypeError, match="symbol must be str"):
            reader.query_instrument_metadata(symbol=1)

    def test_symbol_must_not_be_empty(self):
        reader = _reader()
        with pytest.raises(ValueError, match="symbol must not be empty"):
            reader.query_instrument_metadata(symbol="")

    def test_symbol_must_not_be_whitespace_only(self):
        reader = _reader()
        with pytest.raises(ValueError, match="symbol must not be empty"):
            reader.query_instrument_metadata(symbol="   ")

    def test_invalid_symbol_rejected_before_any_http_call(self):
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        with pytest.raises(TypeError):
            reader.query_instrument_metadata(symbol=1)
        assert api.calls == []

    def test_keyword_only(self):
        reader = _reader()
        with pytest.raises(TypeError):
            reader.query_instrument_metadata("BTCUSDT")


class TestQueryInstrumentMetadata:
    def test_returns_execution_instrument_metadata(self):
        metadata = _reader().query_instrument_metadata(symbol="BTCUSDT")
        assert isinstance(metadata, ExecutionInstrumentMetadata)

    def test_returns_interpreter_result_by_identity(self):
        interpreter = _SpyInterpreter(result=_SENTINEL_METADATA)
        reader = _reader(response_interpreter=interpreter)
        assert reader.query_instrument_metadata(symbol="BTCUSDT") is _SENTINEL_METADATA

    def test_url_built_from_instruments_info_endpoint(self):
        url_builder = _SpyUrlBuilder()
        reader = _reader(url_builder=url_builder)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert url_builder.calls[0]["endpoint"] is BYBIT_INSTRUMENTS_INFO_ENDPOINT

    def test_uses_url_from_builder(self):
        api = _SpyPublicGetApi()
        reader = _reader(url_builder=_SpyUrlBuilder(result="https://custom/x"), public_get_api=api)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert api.calls[0]["url"] == "https://custom/x"

    def test_scope_fixed_to_linear(self):
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert "category=linear" in api.calls[0]["query_string"]

    def test_query_string_includes_requested_symbol(self):
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert "symbol=BTCUSDT" in api.calls[0]["query_string"]

    def test_different_symbol_produces_different_query_string(self):
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="ETHUSDT")
        assert "symbol=ETHUSDT" in api.calls[0]["query_string"]
        assert "symbol=BTCUSDT" not in api.calls[0]["query_string"]

    def test_symbol_with_special_characters_url_encoded(self):
        # No es una whitelist de negocio -- es construcción correcta de la
        # query string ante caracteres que romperían su sintaxis.
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="BTC&USDT")
        assert "&USDT" not in api.calls[0]["query_string"].split("symbol=")[1]

    def test_requested_symbol_forwarded_to_interpreter(self):
        interpreter = _SpyInterpreter()
        reader = _reader(response_interpreter=interpreter)
        reader.query_instrument_metadata(symbol="ETHUSDT")
        assert interpreter.calls[0]["requested_symbol"] == "ETHUSDT"

    def test_response_passed_to_interpreter_by_identity(self):
        response = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (_SENTINEL_ITEM,)}, ret_ext_info={}, time_ms=1,
        )
        interpreter = _SpyInterpreter()
        reader = _reader(
            public_get_api=_SpyPublicGetApi(result=response),
            response_interpreter=interpreter,
        )
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert interpreter.calls[0]["response"] is response

    def test_exactly_one_api_request_call(self):
        api = _SpyPublicGetApi()
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert len(api.calls) == 1

    def test_exactly_one_interpret_call(self):
        interpreter = _SpyInterpreter()
        reader = _reader(response_interpreter=interpreter)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert len(interpreter.calls) == 1


class TestErrorTranslation:
    """Ningún tipo Bybit cruza query_instrument_metadata() -- mismo
    principio que los demás readers del read-side: todo se traduce a
    ExecutionInfrastructureError ya existente, sin inventar jerarquía
    nueva."""

    def test_api_error_translated_to_infrastructure_error(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10001, ret_msg="params error"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_bybit_api_error_does_not_cross_the_port(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10001, ret_msg="params error"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_instrument_metadata(symbol="BTCUSDT")
            assert False, "expected ExecutionInfrastructureError"
        except BybitApiError:
            assert False, "BybitApiError must not cross the read Port"
        except ExecutionInfrastructureError:
            pass

    def test_response_processing_error_from_interpreter_translated(self):
        interpreter = _SpyInterpreter(exc=BybitResponseProcessingError(message="bad schema"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_response_processing_error_from_transport_layer_translated(self):
        api = _SpyPublicGetApi(exc=BybitResponseProcessingError(message="bad utf-8"))
        reader = _reader(public_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_os_error_from_transport_translated(self):
        api = _SpyPublicGetApi(exc=OSError("connection refused"))
        reader = _reader(public_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_original_error_preserved_as_cause(self):
        original = BybitApiError(ret_code=10001, ret_msg="params error")
        interpreter = _SpyInterpreter(exc=original)
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_instrument_metadata(symbol="BTCUSDT")
        except ExecutionInfrastructureError as error:
            assert error.__cause__ is original

    def test_infrastructure_error_message_does_not_leak_ret_msg(self):
        interpreter = _SpyInterpreter(exc=BybitApiError(ret_code=10001, ret_msg="SUPER_SECRET_DETAIL"))
        reader = _reader(response_interpreter=interpreter)
        try:
            reader.query_instrument_metadata(symbol="BTCUSDT")
            assert False
        except ExecutionInfrastructureError as error:
            assert "SUPER_SECRET_DETAIL" not in str(error)

    def test_type_error_from_interpreter_propagates_unwrapped(self):
        interpreter = _SpyInterpreter(exc=TypeError("programming bug"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(TypeError, match="programming bug"):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_runtime_error_from_interpreter_propagates_unwrapped(self):
        interpreter = _SpyInterpreter(exc=RuntimeError("internal bug"))
        reader = _reader(response_interpreter=interpreter)
        with pytest.raises(RuntimeError, match="internal bug"):
            reader.query_instrument_metadata(symbol="BTCUSDT")

    def test_no_catch_all_exception_in_source(self):
        import inspect
        import execution_gateway.bybit_instrument_metadata_reader as module
        assert "except Exception" not in inspect.getsource(module)


class TestNoTrading:
    def test_no_create_order_reference_in_source(self):
        import inspect
        import execution_gateway.bybit_instrument_metadata_reader as module
        src = inspect.getsource(module)
        assert "create_order" not in src
        assert "place_order" not in src
        assert "BybitCreateOrderOperation" not in src
        assert "/v5/order/create" not in src

    def test_does_not_import_execution_gateway_write_types(self):
        import execution_gateway.bybit_instrument_metadata_reader as module
        assert not hasattr(module, "ExecutionGateway")
        assert not hasattr(module, "BybitExecutionGateway")
        assert not hasattr(module, "BybitDemoClient")

    def test_does_not_reference_positions_open_orders_wallet_balance(self):
        import inspect
        import execution_gateway.bybit_instrument_metadata_reader as module
        src = inspect.getsource(module)
        assert "PositionsSnapshot" not in src
        assert "OpenOrdersSnapshot" not in src
        assert "WalletBalanceSnapshot" not in src


class TestNoCacheAcrossCalls:
    """Lección directa del Hito 3.70, aplicada desde el primer commit de
    este hito: la metadata puede cambiar y un futuro consumidor mantendrá
    viva una misma instancia de BybitInstrumentMetadataReader."""

    def test_api_called_exactly_twice_on_two_queries(self):
        api = _SpyPublicGetApi(results=[_SENTINEL_RESPONSE, _SENTINEL_RESPONSE])
        reader = _reader(public_get_api=api)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert len(api.calls) == 2

    def test_interpreter_called_exactly_twice_on_two_queries(self):
        m1 = ExecutionInstrumentMetadata(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
            instrument_status="Trading", contract_type="LinearPerpetual",
            tick_size=Decimal("0.1"), min_price=Decimal("0.1"), max_price=Decimal("100"),
            qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
            server_time_ms=1,
        )
        m2 = ExecutionInstrumentMetadata(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
            instrument_status="Trading", contract_type="LinearPerpetual",
            tick_size=Decimal("0.2"), min_price=Decimal("0.1"), max_price=Decimal("100"),
            qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
            server_time_ms=2,
        )
        interpreter = _SpyInterpreter(results=[m1, m2])
        reader = _reader(response_interpreter=interpreter)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert len(interpreter.calls) == 2

    def test_two_calls_on_same_instance_return_distinct_results_by_identity(self):
        m1 = ExecutionInstrumentMetadata(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
            instrument_status="Trading", contract_type="LinearPerpetual",
            tick_size=Decimal("0.1"), min_price=Decimal("0.1"), max_price=Decimal("100"),
            qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
            server_time_ms=1,
        )
        m2 = ExecutionInstrumentMetadata(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", settlement_asset="USDT",
            instrument_status="Trading", contract_type="LinearPerpetual",
            tick_size=Decimal("0.2"), min_price=Decimal("0.1"), max_price=Decimal("100"),
            qty_step=Decimal("0.1"), min_order_qty=Decimal("0.1"), max_order_qty=Decimal("100"),
            server_time_ms=2,
        )
        interpreter = _SpyInterpreter(results=[m1, m2])
        reader = _reader(response_interpreter=interpreter)
        first = reader.query_instrument_metadata(symbol="BTCUSDT")
        second = reader.query_instrument_metadata(symbol="BTCUSDT")
        assert first is m1
        assert second is m2
        assert first is not second

    def test_second_result_reflects_second_api_response_end_to_end(self):
        item_a = dict(_SENTINEL_ITEM)
        resp1 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (item_a,), "nextPageCursor": ""},
            ret_ext_info={}, time_ms=111,
        )
        resp2 = BybitResponse(
            ret_code=0, ret_msg="OK", result={"list": (item_a,), "nextPageCursor": ""},
            ret_ext_info={}, time_ms=222,
        )
        api = _SpyPublicGetApi(results=[resp1, resp2])
        reader = _reader(public_get_api=api, response_interpreter=BybitInstrumentMetadataResponseInterpreter())
        first = reader.query_instrument_metadata(symbol="BTCUSDT")
        second = reader.query_instrument_metadata(symbol="BTCUSDT")
        assert first.server_time_ms == 111
        assert second.server_time_ms == 222

    def test_different_symbols_on_same_instance_produce_distinct_queries(self):
        api = _SpyPublicGetApi(results=[_SENTINEL_RESPONSE, _SENTINEL_RESPONSE])
        interpreter = _SpyInterpreter()
        reader = _reader(public_get_api=api, response_interpreter=interpreter)
        reader.query_instrument_metadata(symbol="BTCUSDT")
        reader.query_instrument_metadata(symbol="ETHUSDT")
        assert interpreter.calls[0]["requested_symbol"] == "BTCUSDT"
        assert interpreter.calls[1]["requested_symbol"] == "ETHUSDT"

    def test_reader_instance_has_no_cache_attribute_after_query(self):
        reader = _reader()
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert not hasattr(reader, "_cached")
        assert not hasattr(reader, "_cache")
        assert not hasattr(reader, "_last_result")
        assert not hasattr(reader, "_last_metadata")

    def test_two_independent_reader_instances_do_not_share_state(self):
        reader_a = _reader()
        reader_b = _reader()
        assert reader_a is not reader_b
        assert vars(reader_a).keys() == {"_public_get_api", "_url_builder", "_response_interpreter"}

    def test_second_query_after_first_failure_still_calls_api_again(self):
        api = _SpyPublicGetApi(exc=OSError("down"))
        reader = _reader(public_get_api=api)
        with pytest.raises(ExecutionInfrastructureError):
            reader.query_instrument_metadata(symbol="BTCUSDT")
        api._exc = None
        api._result = _SENTINEL_RESPONSE
        reader.query_instrument_metadata(symbol="BTCUSDT")
        assert len(api.calls) == 2
