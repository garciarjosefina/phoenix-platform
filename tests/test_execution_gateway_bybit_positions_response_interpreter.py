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


class TestAccessoryFields:
    """IMPORTANT-2 (auditoría Hito 3.70): leverage y unrealisedPnl son
    accesorios -- Bybit puede devolverlos vacíos/ausentes en respuestas
    válidas (p.ej. cuentas Unified en portfolio margin). Ausentes o vacíos
    no deben abortar la fila ni el snapshot; malformados sí siguen
    fallando cerrado."""

    def test_leverage_empty_string_becomes_none(self):
        snapshot = _interpret(items=[_item(leverage="")])
        assert snapshot.positions[0].leverage is None

    def test_unrealised_pnl_empty_string_becomes_none(self):
        snapshot = _interpret(items=[_item(unrealisedPnl="")])
        assert snapshot.positions[0].unrealized_pnl is None

    def test_leverage_missing_key_becomes_none(self):
        item = _item()
        del item["leverage"]
        snapshot = _interpret(items=[item])
        assert snapshot.positions[0].leverage is None

    def test_unrealised_pnl_missing_key_becomes_none(self):
        item = _item()
        del item["unrealisedPnl"]
        snapshot = _interpret(items=[item])
        assert snapshot.positions[0].unrealized_pnl is None

    def test_essential_fields_still_mapped_when_accessories_empty(self):
        snapshot = _interpret(items=[_item(leverage="", unrealisedPnl="", symbol="ETHUSDT", side="Sell")])
        position = snapshot.positions[0]
        assert position.symbol == "ETHUSDT"
        assert position.side == "sell"
        assert position.leverage is None
        assert position.unrealized_pnl is None

    def test_leverage_present_and_valid_still_becomes_decimal(self):
        snapshot = _interpret(items=[_item(leverage="25")])
        assert snapshot.positions[0].leverage == Decimal("25")

    def test_leverage_malformed_non_empty_still_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(leverage="not-a-number")])

    def test_unrealised_pnl_malformed_non_empty_still_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(unrealisedPnl="not-a-number")])

    def test_leverage_nan_still_rejected_even_though_optional(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(leverage="nan")])

    def test_one_position_with_empty_accessories_does_not_kill_other_positions(self):
        items = [
            _item(symbol="BTCUSDT", leverage="", unrealisedPnl=""),
            _item(symbol="ETHUSDT", leverage="10", unrealisedPnl="5"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.positions) == 2
        by_symbol = {p.symbol: p for p in snapshot.positions}
        assert by_symbol["BTCUSDT"].leverage is None
        assert by_symbol["ETHUSDT"].leverage == Decimal("10")

    def test_essential_fields_remain_mandatory_symbol(self):
        item = _item()
        del item["symbol"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_essential_fields_remain_mandatory_avg_price(self):
        item = _item()
        del item["avgPrice"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])


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


class TestPagination:
    """IMPORTANT-1 (auditoría Hito 3.70): un snapshot truncado servido como
    si fuera completo es la peor falla posible para reconciliación futura.
    No se implementa paginación en este hito -- se falla cerrado en su
    lugar. Cualquier valor truthy de nextPageCursor debe rechazarse."""

    def test_empty_cursor_permitted(self):
        snapshot = _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": ""})
        assert snapshot.positions == ()

    def test_missing_cursor_key_permitted(self):
        # Bybit siempre lo incluye en la práctica, pero la primitive no se
        # acopla a esa garantía: ausencia se trata igual que cadena vacía.
        snapshot = _interpret(result_override={"category": "linear", "list": []})
        assert snapshot.positions == ()

    def test_nonempty_cursor_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": "abc%3D%3D"})

    def test_typical_bybit_cursor_value_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={
                "category": "linear", "list": [_item()], "nextPageCursor": "abc%3D%3D",
            })

    def test_whitespace_cursor_raises(self):
        # Decisión explícita: cualquier valor truthy -- incluido
        # whitespace-only -- se trata como señal de paginación pendiente.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": "   "})

    def test_cursor_present_never_returns_partial_snapshot(self):
        # No debe devolverse ningún PositionsSnapshot -- ni completo ni
        # parcial -- cuando hay señal de paginación pendiente.
        error = None
        try:
            _interpret(result_override={
                "category": "linear", "list": [_item()], "nextPageCursor": "abc",
            })
        except BybitResponseProcessingError as e:
            error = e
        assert error is not None

    def test_cursor_check_triggers_no_second_http_call(self):
        # El interpreter es puro -- no hace I/O de ningún tipo.
        import inspect
        import execution_gateway.bybit_positions_response_interpreter as module
        src = inspect.getsource(module)
        assert "urllib" not in src
        assert "urlopen" not in src
        assert "request" not in src.lower()

    def test_no_pagination_follow_up_implemented(self):
        # Se lee nextPageCursor sólo para fallar cerrado -- no se arma un
        # segundo query string ni se reintenta con el cursor.
        import inspect
        import execution_gateway.bybit_positions_response_interpreter as module
        src = inspect.getsource(module)
        assert "cursor=" not in src
        assert "settleCoin" not in src
