from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_instrument_metadata_response_interpreter import (
    BybitInstrumentMetadataResponseInterpreter,
)
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata


def _price_filter(**overrides):
    defaults = dict(minPrice="0.10", maxPrice="1999999.80", tickSize="0.10")
    defaults.update(overrides)
    return defaults


def _lot_size_filter(**overrides):
    defaults = dict(
        maxOrderQty="1190.000", minOrderQty="0.001", qtyStep="0.001",
        maxMktOrderQty="500.000", minNotionalValue="5",
    )
    defaults.update(overrides)
    return defaults


def _leverage_filter(**overrides):
    defaults = dict(minLeverage="1", maxLeverage="100.00", leverageStep="0.01")
    defaults.update(overrides)
    return defaults


def _item(**overrides):
    defaults = dict(
        symbol="BTCUSDT", contractType="LinearPerpetual", status="Trading",
        baseCoin="BTC", quoteCoin="USDT", settleCoin="USDT",
        priceFilter=_price_filter(), lotSizeFilter=_lot_size_filter(),
        leverageFilter=_leverage_filter(),
    )
    defaults.update(overrides)
    return defaults


def _response(*, ret_code=0, ret_msg="OK", items=None, time_ms=1_700_000_000_000, result_override=None):
    if result_override is not None:
        result = result_override
    else:
        result = {"category": "linear", "list": tuple(items if items is not None else [_item()]), "nextPageCursor": ""}
    return BybitResponse(ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms)


def _interpret(*, requested_symbol="BTCUSDT", **kwargs):
    return BybitInstrumentMetadataResponseInterpreter().interpret(
        response=_response(**kwargs), requested_symbol=requested_symbol
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitInstrumentMetadataResponseInterpreter")
        assert (
            execution_gateway.BybitInstrumentMetadataResponseInterpreter
            is BybitInstrumentMetadataResponseInterpreter
        )

    def test_in_all(self):
        assert "BybitInstrumentMetadataResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitInstrumentMetadataResponseInterpreter().interpret(
                response={"retCode": 0}, requested_symbol="BTCUSDT"
            )

    def test_requested_symbol_must_be_str(self):
        with pytest.raises(TypeError, match="requested_symbol must be str"):
            BybitInstrumentMetadataResponseInterpreter().interpret(
                response=_response(), requested_symbol=1
            )

    def test_requested_symbol_must_not_be_empty(self):
        with pytest.raises(ValueError, match="requested_symbol must not be empty"):
            BybitInstrumentMetadataResponseInterpreter().interpret(
                response=_response(), requested_symbol=""
            )


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10001, ret_msg="params error", items=[])
        assert exc_info.value.ret_code == 10001

    def test_ret_code_checked_before_touching_result(self):
        with pytest.raises(BybitApiError):
            _interpret(ret_code=10001, ret_msg="error", result_override="not-a-mapping")


class TestSuccess:
    def test_returns_execution_instrument_metadata(self):
        metadata = _interpret()
        assert isinstance(metadata, ExecutionInstrumentMetadata)

    def test_symbol_mapped(self):
        metadata = _interpret(items=[_item(symbol="BTCUSDT")])
        assert metadata.symbol == "BTCUSDT"

    def test_base_quote_settlement_mapped(self):
        metadata = _interpret(items=[_item(baseCoin="BTC", quoteCoin="USDT", settleCoin="USDT")])
        assert metadata.base_asset == "BTC"
        assert metadata.quote_asset == "USDT"
        assert metadata.settlement_asset == "USDT"

    def test_status_and_contract_type_preserved_verbatim(self):
        metadata = _interpret(items=[_item(status="Trading", contractType="LinearPerpetual")])
        assert metadata.instrument_status == "Trading"
        assert metadata.contract_type == "LinearPerpetual"

    def test_unanticipated_status_value_not_rejected(self):
        # El universo completo de status no está documentado -- no se
        # inventa un enum cerrado que bloquee valores legítimos futuros.
        metadata = _interpret(items=[_item(status="SomeFutureStatus")])
        assert metadata.instrument_status == "SomeFutureStatus"

    def test_price_filter_mapped(self):
        metadata = _interpret(items=[_item(priceFilter=_price_filter(
            tickSize="0.5", minPrice="1.5", maxPrice="99999",
        ))])
        assert metadata.tick_size == Decimal("0.5")
        assert metadata.min_price == Decimal("1.5")
        assert metadata.max_price == Decimal("99999")

    def test_lot_size_filter_mapped(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(
            qtyStep="0.01", minOrderQty="0.1", maxOrderQty="500",
        ))])
        assert metadata.qty_step == Decimal("0.01")
        assert metadata.min_order_qty == Decimal("0.1")
        assert metadata.max_order_qty == Decimal("500")

    def test_max_market_order_qty_distinct_from_max_order_qty(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(
            maxOrderQty="1190.000", maxMktOrderQty="500.000",
        ))])
        assert metadata.max_order_qty == Decimal("1190.000")
        assert metadata.max_market_order_qty == Decimal("500.000")
        assert metadata.max_order_qty != metadata.max_market_order_qty

    def test_min_notional_value_mapped(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(minNotionalValue="10"))])
        assert metadata.min_notional_value == Decimal("10")

    def test_leverage_filter_mapped(self):
        metadata = _interpret(items=[_item(leverageFilter=_leverage_filter(
            minLeverage="2", maxLeverage="50", leverageStep="1",
        ))])
        assert metadata.min_leverage == Decimal("2")
        assert metadata.max_leverage == Decimal("50")
        assert metadata.leverage_step == Decimal("1")

    def test_server_time_populated_from_response_envelope(self):
        metadata = _interpret(time_ms=1_712_345_678_901)
        assert metadata.server_time_ms == 1_712_345_678_901


class TestSymbolIdentity:
    """Sección 5/17 del Hito 3.73: identidad inequívoca del instrumento."""

    def test_remote_symbol_mismatch_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(requested_symbol="BTCUSDT", items=[_item(symbol="ETHUSDT")])

    def test_empty_list_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[])

    def test_two_instruments_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(symbol="BTCUSDT"), _item(symbol="BTCUSDT")])

    def test_two_instruments_never_takes_first(self):
        # No debe silenciosamente tomar el primero de una lista ambigua --
        # verificado explícitamente además del test anterior.
        error = None
        try:
            _interpret(items=[_item(symbol="BTCUSDT"), _item(symbol="ETHUSDT")])
        except BybitResponseProcessingError as e:
            error = e
        assert error is not None

    def test_empty_symbol_in_response_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(symbol="")])

    def test_symbol_case_mismatch_fails_closed(self):
        # Comparación exacta por valor -- sin normalización de casing.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(requested_symbol="BTCUSDT", items=[_item(symbol="btcusdt")])

    def test_exact_symbol_match_succeeds(self):
        metadata = _interpret(requested_symbol="BTCUSDT", items=[_item(symbol="BTCUSDT")])
        assert metadata.symbol == "BTCUSDT"


class TestZeroAndEmptySemantics:
    """Sección 7 del Hito 3.73: matriz de vacíos/ceros por campo."""

    def test_max_market_order_qty_empty_becomes_none(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(maxMktOrderQty=""))])
        assert metadata.max_market_order_qty is None

    def test_max_market_order_qty_missing_key_becomes_none(self):
        lsf = _lot_size_filter()
        del lsf["maxMktOrderQty"]
        metadata = _interpret(items=[_item(lotSizeFilter=lsf)])
        assert metadata.max_market_order_qty is None

    def test_max_market_order_qty_zero_preserved_not_none(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(maxMktOrderQty="0"))])
        assert metadata.max_market_order_qty == Decimal("0")

    def test_min_notional_value_empty_becomes_none(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(minNotionalValue=""))])
        assert metadata.min_notional_value is None

    def test_min_notional_value_missing_key_becomes_none(self):
        lsf = _lot_size_filter()
        del lsf["minNotionalValue"]
        metadata = _interpret(items=[_item(lotSizeFilter=lsf)])
        assert metadata.min_notional_value is None

    def test_min_notional_value_zero_preserved_not_none(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(minNotionalValue="0"))])
        assert metadata.min_notional_value == Decimal("0")

    def test_leverage_filter_entirely_absent_yields_none_fields(self):
        item = _item()
        del item["leverageFilter"]
        metadata = _interpret(items=[item])
        assert metadata.min_leverage is None
        assert metadata.max_leverage is None
        assert metadata.leverage_step is None

    def test_leverage_filter_present_but_fields_empty(self):
        metadata = _interpret(items=[_item(leverageFilter=_leverage_filter(
            minLeverage="", maxLeverage="", leverageStep="",
        ))])
        assert metadata.min_leverage is None
        assert metadata.max_leverage is None
        assert metadata.leverage_step is None

    def test_accessory_empty_does_not_abort_metadata(self):
        metadata = _interpret(items=[_item(
            lotSizeFilter=_lot_size_filter(maxMktOrderQty="", minNotionalValue=""),
            leverageFilter=_leverage_filter(minLeverage="", maxLeverage="", leverageStep=""),
        )])
        assert isinstance(metadata, ExecutionInstrumentMetadata)
        assert metadata.symbol == "BTCUSDT"

    def test_max_order_qty_zero_preserved_not_rejected(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(maxOrderQty="0"))])
        assert metadata.max_order_qty == Decimal("0")

    def test_min_price_zero_preserved_not_rejected(self):
        metadata = _interpret(items=[_item(priceFilter=_price_filter(minPrice="0"))])
        assert metadata.min_price == Decimal("0")


class TestNumerics:
    def test_high_precision_decimal_preserved(self):
        metadata = _interpret(items=[_item(priceFilter=_price_filter(tickSize="0.123456789"))])
        assert metadata.tick_size == Decimal("0.123456789")

    def test_very_small_qty_step_preserved(self):
        metadata = _interpret(items=[_item(lotSizeFilter=_lot_size_filter(qtyStep="0.00000001"))])
        assert metadata.qty_step == Decimal("0.00000001")

    def test_very_large_max_price_preserved(self):
        metadata = _interpret(items=[_item(priceFilter=_price_filter(maxPrice="99999999999.99"))])
        assert metadata.max_price == Decimal("99999999999.99")

    def test_never_silently_converts_to_float(self):
        metadata = _interpret(items=[_item(priceFilter=_price_filter(tickSize="0.1"))])
        assert isinstance(metadata.tick_size, Decimal)
        assert metadata.tick_size == Decimal("0.1")

    def test_nan_tick_size_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=_price_filter(tickSize="nan"))])

    def test_infinity_max_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=_price_filter(maxPrice="inf"))])

    def test_nan_qty_step_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=_lot_size_filter(qtyStep="nan"))])

    def test_infinity_min_order_qty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=_lot_size_filter(minOrderQty="inf"))])

    def test_negative_tick_size_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=_price_filter(tickSize="-0.1"))])

    def test_negative_min_order_qty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=_lot_size_filter(minOrderQty="-0.1"))])

    def test_nan_leverage_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(leverageFilter=_leverage_filter(maxLeverage="nan"))])


class TestPagination:
    def test_empty_cursor_permitted(self):
        metadata = _interpret(result_override={
            "category": "linear", "list": (_item(),), "nextPageCursor": "",
        })
        assert metadata.symbol == "BTCUSDT"

    def test_missing_cursor_key_permitted(self):
        metadata = _interpret(result_override={"category": "linear", "list": (_item(),)})
        assert metadata.symbol == "BTCUSDT"

    def test_nonempty_cursor_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={
                "category": "linear", "list": (_item(),), "nextPageCursor": "abc%3D%3D",
            })

    def test_whitespace_cursor_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={
                "category": "linear", "list": (_item(),), "nextPageCursor": "   ",
            })

    def test_cursor_present_never_returns_partial_metadata(self):
        error = None
        try:
            _interpret(result_override={
                "category": "linear", "list": (_item(),), "nextPageCursor": "abc",
            })
        except BybitResponseProcessingError as e:
            error = e
        assert error is not None


class TestMalformedResponse:
    def test_result_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override="not-a-mapping")

    def test_result_list_key_missing(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear"})

    def test_list_not_a_tuple(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": "not-a-list"})

    def test_list_item_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=["not-a-dict"])

    def test_symbol_missing(self):
        item = _item()
        del item["symbol"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_base_coin_missing(self):
        item = _item()
        del item["baseCoin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_quote_coin_missing(self):
        item = _item()
        del item["quoteCoin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_settle_coin_missing(self):
        item = _item()
        del item["settleCoin"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_status_missing(self):
        item = _item()
        del item["status"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_contract_type_missing(self):
        item = _item()
        del item["contractType"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_price_filter_missing(self):
        item = _item()
        del item["priceFilter"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_price_filter_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter="not-a-mapping")])

    def test_price_filter_tick_size_missing(self):
        pf = _price_filter()
        del pf["tickSize"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=pf)])

    def test_price_filter_min_price_missing(self):
        pf = _price_filter()
        del pf["minPrice"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=pf)])

    def test_price_filter_max_price_missing(self):
        pf = _price_filter()
        del pf["maxPrice"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=pf)])

    def test_lot_size_filter_missing(self):
        item = _item()
        del item["lotSizeFilter"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_lot_size_filter_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter="not-a-mapping")])

    def test_lot_size_filter_qty_step_missing(self):
        lsf = _lot_size_filter()
        del lsf["qtyStep"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=lsf)])

    def test_lot_size_filter_min_order_qty_missing(self):
        lsf = _lot_size_filter()
        del lsf["minOrderQty"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=lsf)])

    def test_lot_size_filter_max_order_qty_missing(self):
        lsf = _lot_size_filter()
        del lsf["maxOrderQty"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(lotSizeFilter=lsf)])

    def test_tick_size_malformed_string(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(priceFilter=_price_filter(tickSize="not-a-number"))])

    def test_leverage_filter_malformed_type_not_a_mapping_tolerated(self):
        # leverageFilter de tipo inesperado (no Mapping) se trata como
        # ausente -- accesorio, no aborta.
        metadata = _interpret(items=[_item(leverageFilter="not-a-mapping")])
        assert metadata.min_leverage is None


class TestPurity:
    def test_public_contract_does_not_expose_bybit_vocabulary(self):
        metadata = _interpret()
        public = {k for k in vars(metadata) if not k.startswith("_")}
        forbidden = {"retCode", "retMsg", "baseCoin", "quoteCoin", "settleCoin",
                     "contractType", "priceFilter", "lotSizeFilter", "leverageFilter"}
        assert public.isdisjoint(forbidden)

    def test_no_raw_dict_leaks_into_metadata(self):
        metadata = _interpret()
        assert not hasattr(metadata, "result")
        assert not hasattr(metadata, "raw")
