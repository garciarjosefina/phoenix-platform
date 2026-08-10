from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_positions_response_interpreter import BybitPositionsResponseInterpreter
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.positions_contracts import PositionsSnapshot


def _item(**overrides):
    defaults = dict(
        positionIdx=0,
        symbol="BTCUSDT",
        side="Buy",
        size="0.01",
        avgPrice="60000.5",
        leverage="10",
        unrealisedPnl="5.25",
    )
    defaults.update(overrides)
    return defaults


def _response(*, ret_code=0, ret_msg="OK", items=None, time_ms=1_700_000_000_000, result_override=None):
    if result_override is not None:
        result = result_override
    else:
        result = {"category": "linear", "list": list(items or []), "nextPageCursor": ""}
    return BybitResponse(ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms)


def _interpret(**kwargs):
    return BybitPositionsResponseInterpreter().interpret(response=_response(**kwargs))


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitPositionsResponseInterpreter")
        assert execution_gateway.BybitPositionsResponseInterpreter is BybitPositionsResponseInterpreter

    def test_in_all(self):
        assert "BybitPositionsResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitPositionsResponseInterpreter().interpret(response={"retCode": 0})


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10003, ret_msg="API key is invalid", items=[])
        assert exc_info.value.ret_code == 10003
        assert exc_info.value.ret_msg == "API key is invalid"

    def test_ret_code_checked_before_touching_result(self):
        # result malformado no debe importar si ret_code ya indica error
        with pytest.raises(BybitApiError):
            _interpret(ret_code=10004, ret_msg="error sign", result_override="not-a-mapping")


class TestEmptyResponse:
    def test_no_positions_returns_empty_tuple(self):
        snapshot = _interpret(items=[])
        assert isinstance(snapshot, PositionsSnapshot)
        assert snapshot.positions == ()

    def test_empty_response_is_not_an_error(self):
        _interpret(items=[])  # no debe lanzar

    def test_server_time_preserved_on_empty_response(self):
        snapshot = _interpret(items=[], time_ms=1_712_345_678_901)
        assert snapshot.server_time_ms == 1_712_345_678_901


class TestSinglePositionLong:
    def test_maps_symbol(self):
        snapshot = _interpret(items=[_item(symbol="BTCUSDT")])
        assert snapshot.positions[0].symbol == "BTCUSDT"

    def test_maps_side_buy_to_lowercase_buy(self):
        snapshot = _interpret(items=[_item(side="Buy")])
        assert snapshot.positions[0].side == "buy"

    def test_maps_quantity_as_decimal(self):
        snapshot = _interpret(items=[_item(size="0.015")])
        assert snapshot.positions[0].quantity == Decimal("0.015")

    def test_maps_entry_price_from_avg_price(self):
        snapshot = _interpret(items=[_item(avgPrice="60123.45")])
        assert snapshot.positions[0].entry_price == Decimal("60123.45")

    def test_maps_leverage(self):
        snapshot = _interpret(items=[_item(leverage="25")])
        assert snapshot.positions[0].leverage == Decimal("25")

    def test_maps_unrealized_pnl(self):
        snapshot = _interpret(items=[_item(unrealisedPnl="123.45")])
        assert snapshot.positions[0].unrealized_pnl == Decimal("123.45")

    def test_exactly_one_position_in_snapshot(self):
        snapshot = _interpret(items=[_item()])
        assert len(snapshot.positions) == 1


class TestSinglePositionShort:
    def test_maps_side_sell_to_lowercase_sell(self):
        snapshot = _interpret(items=[_item(side="Sell", symbol="ETHUSDT")])
        assert snapshot.positions[0].side == "sell"

    def test_short_position_with_negative_pnl(self):
        snapshot = _interpret(items=[_item(side="Sell", unrealisedPnl="-42.10")])
        assert snapshot.positions[0].unrealized_pnl == Decimal("-42.10")


class TestMultiplePositions:
    def test_no_loss_no_duplication(self):
        items = [_item(symbol=f"SYM{i}USDT") for i in range(5)]
        snapshot = _interpret(items=items)
        assert len(snapshot.positions) == 5

    def test_deterministic_order_matches_input(self):
        items = [
            _item(symbol="BTCUSDT"),
            _item(symbol="ETHUSDT"),
            _item(symbol="SOLUSDT"),
        ]
        snapshot = _interpret(items=items)
        assert [p.symbol for p in snapshot.positions] == ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    def test_two_calls_produce_same_order(self):
        items = [_item(symbol="BTCUSDT"), _item(symbol="ETHUSDT")]
        s1 = _interpret(items=items)
        s2 = _interpret(items=items)
        assert [p.symbol for p in s1.positions] == [p.symbol for p in s2.positions]


class TestHedgeMode:
    def test_two_legs_same_symbol_both_preserved(self):
        items = [
            _item(positionIdx=1, symbol="BTCUSDT", side="Buy", size="0.02", unrealisedPnl="10.5"),
            _item(positionIdx=2, symbol="BTCUSDT", side="Sell", size="0.01", unrealisedPnl="-3.2"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.positions) == 2

    def test_legs_not_collapsed_by_side(self):
        items = [
            _item(positionIdx=1, symbol="BTCUSDT", side="Buy", size="0.02"),
            _item(positionIdx=2, symbol="BTCUSDT", side="Sell", size="0.01"),
        ]
        snapshot = _interpret(items=items)
        sides = {p.side for p in snapshot.positions}
        assert sides == {"buy", "sell"}

    def test_both_legs_keep_own_quantity(self):
        items = [
            _item(positionIdx=1, symbol="BTCUSDT", side="Buy", size="0.02"),
            _item(positionIdx=2, symbol="BTCUSDT", side="Sell", size="0.01"),
        ]
        snapshot = _interpret(items=items)
        quantities = {p.side: p.quantity for p in snapshot.positions}
        assert quantities == {"buy": Decimal("0.02"), "sell": Decimal("0.01")}

    def test_positionidx_not_exposed_anywhere(self):
        items = [_item(positionIdx=1, symbol="BTCUSDT", side="Buy")]
        snapshot = _interpret(items=items)
        public = {k for k in vars(snapshot.positions[0]) if not k.startswith("_")}
        assert "positionIdx" not in public
        assert "position_idx" not in public


class TestZeroSizePositions:
    def test_zero_size_flat_placeholder_excluded(self):
        items = [_item(symbol="ETHUSDT", side="None", size="0", avgPrice="0", unrealisedPnl="0")]
        snapshot = _interpret(items=items)
        assert snapshot.positions == ()

    def test_zero_size_mixed_with_real_position(self):
        items = [
            _item(symbol="ETHUSDT", side="None", size="0", avgPrice="0", unrealisedPnl="0"),
            _item(symbol="BTCUSDT", side="Buy", size="0.01"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.positions) == 1
        assert snapshot.positions[0].symbol == "BTCUSDT"

    def test_negative_size_is_malformed(self):
        items = [_item(size="-0.01")]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=items)


class TestNumerics:
    def test_small_quantity_preserved_exactly(self):
        snapshot = _interpret(items=[_item(size="0.00000001")])
        assert snapshot.positions[0].quantity == Decimal("0.00000001")

    def test_many_decimal_places_price_preserved(self):
        snapshot = _interpret(items=[_item(avgPrice="60123.123456789")])
        assert snapshot.positions[0].entry_price == Decimal("60123.123456789")

    def test_large_quantity_preserved(self):
        snapshot = _interpret(items=[_item(size="1000000.5")])
        assert snapshot.positions[0].quantity == Decimal("1000000.5")

    def test_never_silently_converts_to_float(self):
        snapshot = _interpret(items=[_item(size="0.1", avgPrice="0.3")])
        assert isinstance(snapshot.positions[0].quantity, Decimal)
        assert isinstance(snapshot.positions[0].entry_price, Decimal)
        # 0.1 no es representable exacto en float -- si hubiera pasado por
        # float en algún punto, esta comparación exacta fallaría.
        assert snapshot.positions[0].quantity == Decimal("0.1")

    def test_nan_size_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(size="nan")])

    def test_infinity_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(avgPrice="inf")])

    def test_nan_leverage_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(leverage="nan")])

    def test_nan_unrealized_pnl_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(unrealisedPnl="nan")])


class TestMalformedResponse:
    def test_result_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override="not-a-mapping")

    def test_result_list_key_missing(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear"})

    def test_list_not_a_list(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": "not-a-list"})

    def test_list_item_not_a_mapping(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": ["not-a-dict"]})

    def test_symbol_invalid_type(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(symbol=123)])

    def test_side_unknown_value(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(side="Unknown")])

    def test_size_invalid_string(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(size="abc")])

    def test_size_missing(self):
        item = _item()
        del item["size"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_size_null(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(size=None)])

    def test_avg_price_invalid(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(avgPrice="not-a-number")])

    def test_avg_price_missing(self):
        item = _item()
        del item["avgPrice"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_leverage_missing(self):
        item = _item()
        del item["leverage"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_unrealised_pnl_missing(self):
        item = _item()
        del item["unrealisedPnl"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_side_missing(self):
        item = _item()
        del item["side"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_symbol_missing(self):
        item = _item()
        del item["symbol"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_one_malformed_item_among_valid_ones_fails_closed(self):
        items = [_item(symbol="BTCUSDT"), _item(symbol="ETHUSDT", side="Unknown")]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=items)


class TestPurity:
    def test_public_contract_does_not_expose_bybit_vocabulary(self):
        snapshot = _interpret(items=[_item()])
        position = snapshot.positions[0]
        public = {k for k in vars(position) if not k.startswith("_")}
        forbidden = {"retCode", "retMsg", "positionIdx", "avgPrice", "unrealisedPnl"}
        assert public.isdisjoint(forbidden)

    def test_no_raw_dict_leaks_into_snapshot(self):
        snapshot = _interpret(items=[_item()])
        assert not hasattr(snapshot, "result")
        assert not hasattr(snapshot, "raw")
