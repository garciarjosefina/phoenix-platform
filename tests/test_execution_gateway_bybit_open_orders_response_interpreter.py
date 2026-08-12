from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_open_orders_response_interpreter import BybitOpenOrdersResponseInterpreter
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.open_orders_contracts import OpenOrdersSnapshot


def _item(**overrides):
    defaults = dict(
        orderId="bybit-order-1",
        orderLinkId="phoenix-order-1",
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="0.01",
        price="60000.5",
        cumExecQty="0",
        orderStatus="New",
        reduceOnly=False,
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
    return BybitOpenOrdersResponseInterpreter().interpret(response=_response(**kwargs))


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitOpenOrdersResponseInterpreter")
        assert execution_gateway.BybitOpenOrdersResponseInterpreter is BybitOpenOrdersResponseInterpreter

    def test_in_all(self):
        assert "BybitOpenOrdersResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitOpenOrdersResponseInterpreter().interpret(response={"retCode": 0})


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10003, ret_msg="API key is invalid", items=[])
        assert exc_info.value.ret_code == 10003

    def test_ret_code_checked_before_touching_result(self):
        with pytest.raises(BybitApiError):
            _interpret(ret_code=10004, ret_msg="error sign", result_override="not-a-mapping")


class TestEmptyResponse:
    def test_no_orders_returns_empty_tuple(self):
        snapshot = _interpret(items=[])
        assert isinstance(snapshot, OpenOrdersSnapshot)
        assert snapshot.orders == ()

    def test_empty_response_is_not_an_error(self):
        _interpret(items=[])

    def test_server_time_preserved_on_empty_response(self):
        snapshot = _interpret(items=[], time_ms=1_712_345_678_901)
        assert snapshot.server_time_ms == 1_712_345_678_901


class TestIdentity:
    def test_order_link_id_and_order_id_preserved_separately(self):
        snapshot = _interpret(items=[_item(orderId="bybit-99", orderLinkId="phoenix-42")])
        order = snapshot.orders[0]
        assert order.exchange_order_id == "bybit-99"
        assert order.order_id == "phoenix-42"

    def test_order_link_id_empty_becomes_none(self):
        snapshot = _interpret(items=[_item(orderLinkId="")])
        assert snapshot.orders[0].order_id is None

    def test_order_link_id_missing_key_becomes_none(self):
        item = _item()
        del item["orderLinkId"]
        snapshot = _interpret(items=[item])
        assert snapshot.orders[0].order_id is None

    def test_orphan_order_not_dropped_from_snapshot(self):
        # Una orden sin identidad de dominio es exactamente lo que un
        # futuro reconciliador debe poder detectar -- nunca se oculta.
        snapshot = _interpret(items=[_item(orderLinkId="")])
        assert len(snapshot.orders) == 1
        assert snapshot.orders[0].exchange_order_id == "bybit-order-1"

    def test_exchange_order_id_always_required(self):
        item = _item()
        del item["orderId"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_exchange_order_id_empty_is_malformed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderId="")])

    def test_order_link_id_never_used_as_exchange_id(self):
        snapshot = _interpret(items=[_item(orderId="X", orderLinkId="Y")])
        order = snapshot.orders[0]
        assert order.exchange_order_id == "X"
        assert order.order_id == "Y"
        assert order.exchange_order_id != order.order_id


class TestLongShort:
    def test_buy_maps_to_lowercase_buy(self):
        snapshot = _interpret(items=[_item(side="Buy")])
        assert snapshot.orders[0].side == "buy"

    def test_sell_maps_to_lowercase_sell(self):
        snapshot = _interpret(items=[_item(side="Sell")])
        assert snapshot.orders[0].side == "sell"

    def test_side_unknown_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(side="Unknown")])


class TestOrderTypes:
    def test_limit_maps_correctly(self):
        snapshot = _interpret(items=[_item(orderType="Limit", price="100")])
        order = snapshot.orders[0]
        assert order.order_type == "limit"
        assert order.price == Decimal("100")

    def test_market_maps_correctly(self):
        snapshot = _interpret(items=[_item(orderType="Market", price="")])
        order = snapshot.orders[0]
        assert order.order_type == "market"
        assert order.price is None

    def test_market_with_missing_price_key(self):
        item = _item(orderType="Market")
        del item["price"]
        snapshot = _interpret(items=[item])
        assert snapshot.orders[0].price is None

    def test_price_present_and_valid_becomes_decimal(self):
        snapshot = _interpret(items=[_item(price="60123.45")])
        assert snapshot.orders[0].price == Decimal("60123.45")

    def test_price_malformed_non_empty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="not-a-number")])

    def test_order_type_unknown_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderType="Conditional")])


class TestPriceSemantics:
    """IMPORTANT-1 (auditoría del Hito 3.71): price="0" es una respuesta
    legítima real de Bybit para market orders, no sólo price="" -- ambas
    representan "sin precio preestablecido", nunca deben abortar el
    snapshot."""

    def test_market_empty_string_becomes_none(self):
        snapshot = _interpret(items=[_item(orderType="Market", price="")])
        assert snapshot.orders[0].price is None

    def test_market_zero_becomes_none(self):
        snapshot = _interpret(items=[_item(orderType="Market", price="0")])
        assert snapshot.orders[0].price is None

    def test_market_zero_point_zero_becomes_none(self):
        # Comparado por valor tras parsear, no por texto -- "0.0" es
        # equivalente a "0" para esta semántica.
        snapshot = _interpret(items=[_item(orderType="Market", price="0.00")])
        assert snapshot.orders[0].price is None

    def test_market_missing_key_becomes_none(self):
        item = _item(orderType="Market")
        del item["price"]
        snapshot = _interpret(items=[item])
        assert snapshot.orders[0].price is None

    def test_limit_valid_price_becomes_decimal(self):
        snapshot = _interpret(items=[_item(orderType="Limit", price="60000.5")])
        assert snapshot.orders[0].price == Decimal("60000.5")

    def test_negative_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="-1")])

    def test_malformed_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="abc")])

    def test_nan_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="nan")])

    def test_infinity_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="inf")])

    def test_market_zero_price_among_valid_orders_does_not_abort_snapshot(self):
        items = [
            _item(orderId="1", orderType="Market", price="0"),
            _item(orderId="2", orderType="Limit", price="60000"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.orders) == 2
        by_id = {o.exchange_order_id: o for o in snapshot.orders}
        assert by_id["1"].price is None
        assert by_id["2"].price == Decimal("60000")


class TestPartialFill:
    def test_new_order_zero_filled(self):
        snapshot = _interpret(items=[_item(orderStatus="New", cumExecQty="0")])
        order = snapshot.orders[0]
        assert order.status == "new"
        assert order.filled_quantity == Decimal("0")

    def test_partially_filled_status_and_quantity(self):
        snapshot = _interpret(items=[_item(orderStatus="PartiallyFilled", qty="1", cumExecQty="0.4")])
        order = snapshot.orders[0]
        assert order.status == "partially_filled"
        assert order.quantity == Decimal("1")
        assert order.filled_quantity == Decimal("0.4")

    def test_untriggered_status(self):
        snapshot = _interpret(items=[_item(orderStatus="Untriggered")])
        assert snapshot.orders[0].status == "untriggered"

    def test_filled_quantity_precision_preserved(self):
        snapshot = _interpret(items=[_item(cumExecQty="0.123456789")])
        assert snapshot.orders[0].filled_quantity == Decimal("0.123456789")

    def test_cum_exec_qty_never_converted_via_float(self):
        snapshot = _interpret(items=[_item(cumExecQty="0.1")])
        assert isinstance(snapshot.orders[0].filled_quantity, Decimal)
        assert snapshot.orders[0].filled_quantity == Decimal("0.1")

    def test_status_terminal_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus="Filled")])

    def test_status_cancelled_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus="Cancelled")])


class TestStatusSemantics:
    """IMPORTANT-2 (auditoría del Hito 3.71): "Triggered" es el estado
    transitorio legítimo de una orden condicional en la transición
    Untriggered -> Triggered -> New, observable en una carrera de lectura
    real -- no debe abortar el snapshot ni colapsarse silenciosamente a
    otro estado."""

    def test_new_maps_to_new(self):
        snapshot = _interpret(items=[_item(orderStatus="New")])
        assert snapshot.orders[0].status == "new"

    def test_partially_filled_maps_to_partially_filled(self):
        snapshot = _interpret(items=[_item(orderStatus="PartiallyFilled")])
        assert snapshot.orders[0].status == "partially_filled"

    def test_untriggered_maps_to_untriggered(self):
        snapshot = _interpret(items=[_item(orderStatus="Untriggered")])
        assert snapshot.orders[0].status == "untriggered"

    def test_triggered_maps_to_triggered(self):
        snapshot = _interpret(items=[_item(orderStatus="Triggered")])
        assert snapshot.orders[0].status == "triggered"

    def test_triggered_not_collapsed_to_new(self):
        snapshot = _interpret(items=[_item(orderStatus="Triggered")])
        assert snapshot.orders[0].status != "new"

    def test_illegitimate_terminal_status_still_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus="Deactivated")])

    def test_unknown_status_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus="SomethingElse")])

    def test_triggered_order_among_valid_orders_does_not_abort_snapshot(self):
        items = [
            _item(orderId="1", orderStatus="Triggered"),
            _item(orderId="2", orderStatus="New"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.orders) == 2
        by_id = {o.exchange_order_id: o for o in snapshot.orders}
        assert by_id["1"].status == "triggered"
        assert by_id["2"].status == "new"


class TestReduceOnly:
    def test_true_preserved(self):
        snapshot = _interpret(items=[_item(reduceOnly=True)])
        assert snapshot.orders[0].reduce_only is True

    def test_false_preserved(self):
        snapshot = _interpret(items=[_item(reduceOnly=False)])
        assert snapshot.orders[0].reduce_only is False

    def test_string_true_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(reduceOnly="true")])

    def test_int_one_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(reduceOnly=1)])

    def test_missing_key_rejected(self):
        item = _item()
        del item["reduceOnly"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])


class TestMultipleOrders:
    def test_no_loss_no_duplication(self):
        items = [_item(orderId=f"id-{i}") for i in range(5)]
        snapshot = _interpret(items=items)
        assert len(snapshot.orders) == 5

    def test_deterministic_order_matches_input(self):
        items = [_item(orderId="1"), _item(orderId="2"), _item(orderId="3")]
        snapshot = _interpret(items=items)
        assert [o.exchange_order_id for o in snapshot.orders] == ["1", "2", "3"]

    def test_two_calls_produce_same_order(self):
        items = [_item(orderId="1"), _item(orderId="2")]
        s1 = _interpret(items=items)
        s2 = _interpret(items=items)
        assert [o.exchange_order_id for o in s1.orders] == [o.exchange_order_id for o in s2.orders]


class TestNoAccidentalDeduplication:
    def test_same_symbol_side_price_different_orders_not_collapsed(self):
        # La identidad es orderId/orderLinkId, no atributos económicos.
        items = [
            _item(orderId="A", orderLinkId="link-a", symbol="BTCUSDT", side="Buy", price="60000"),
            _item(orderId="B", orderLinkId="link-b", symbol="BTCUSDT", side="Buy", price="60000"),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.orders) == 2
        assert {o.exchange_order_id for o in snapshot.orders} == {"A", "B"}

    def test_two_orphans_same_symbol_not_collapsed(self):
        items = [
            _item(orderId="A", orderLinkId=""),
            _item(orderId="B", orderLinkId=""),
        ]
        snapshot = _interpret(items=items)
        assert len(snapshot.orders) == 2


class TestPagination:
    def test_empty_cursor_permitted(self):
        snapshot = _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": ""})
        assert snapshot.orders == ()

    def test_missing_cursor_key_permitted(self):
        snapshot = _interpret(result_override={"category": "linear", "list": []})
        assert snapshot.orders == ()

    def test_nonempty_cursor_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": "abc%3D%3D"})

    def test_typical_bybit_cursor_value_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={
                "category": "linear", "list": [_item()], "nextPageCursor": "abc%3D%3D",
            })

    def test_whitespace_cursor_raises(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [], "nextPageCursor": "   "})

    def test_cursor_present_never_returns_partial_snapshot(self):
        error = None
        try:
            _interpret(result_override={
                "category": "linear", "list": [_item()], "nextPageCursor": "abc",
            })
        except BybitResponseProcessingError as e:
            error = e
        assert error is not None

    def test_no_pagination_follow_up_implemented(self):
        import inspect
        import execution_gateway.bybit_open_orders_response_interpreter as module
        src = inspect.getsource(module)
        assert "urllib" not in src
        assert "urlopen" not in src


class TestNumerics:
    def test_small_quantity_preserved_exactly(self):
        snapshot = _interpret(items=[_item(qty="0.00000001")])
        assert snapshot.orders[0].quantity == Decimal("0.00000001")

    def test_many_decimal_places_price_preserved(self):
        snapshot = _interpret(items=[_item(price="60123.123456789")])
        assert snapshot.orders[0].price == Decimal("60123.123456789")

    def test_large_quantity_preserved(self):
        snapshot = _interpret(items=[_item(qty="1000000.5")])
        assert snapshot.orders[0].quantity == Decimal("1000000.5")

    def test_never_silently_converts_to_float(self):
        snapshot = _interpret(items=[_item(qty="0.1", price="0.3")])
        assert isinstance(snapshot.orders[0].quantity, Decimal)
        assert snapshot.orders[0].quantity == Decimal("0.1")

    def test_nan_qty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="nan")])

    def test_infinity_price_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(price="inf")])

    def test_nan_cum_exec_qty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(cumExecQty="nan")])

    def test_negative_qty_rejected(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="-0.01")])


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

    def test_symbol_missing(self):
        item = _item()
        del item["symbol"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_side_missing(self):
        item = _item()
        del item["side"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_qty_missing(self):
        item = _item()
        del item["qty"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_qty_invalid_string(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="abc")])

    def test_cum_exec_qty_missing(self):
        item = _item()
        del item["cumExecQty"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_cum_exec_qty_invalid_string(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(cumExecQty="abc")])

    def test_order_status_missing(self):
        item = _item()
        del item["orderStatus"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_order_type_missing(self):
        item = _item()
        del item["orderType"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_one_malformed_item_among_valid_ones_fails_closed(self):
        items = [_item(orderId="1"), _item(orderId="2", side="Unknown")]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=items)


class TestPurity:
    def test_public_contract_does_not_expose_bybit_vocabulary(self):
        snapshot = _interpret(items=[_item()])
        order = snapshot.orders[0]
        public = {k for k in vars(order) if not k.startswith("_")}
        forbidden = {"retCode", "retMsg", "orderId", "orderLinkId", "orderStatus", "cumExecQty", "reduceOnly", "orderType"}
        assert public.isdisjoint(forbidden)

    def test_no_raw_dict_leaks_into_snapshot(self):
        snapshot = _interpret(items=[_item()])
        assert not hasattr(snapshot, "result")
        assert not hasattr(snapshot, "raw")
