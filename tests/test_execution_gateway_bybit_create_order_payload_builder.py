from decimal import Decimal

import pytest

from execution_gateway import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_payload_builder import (
    BybitCreateOrderPayloadBuilder,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _market(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Market",
        quantity=Decimal("0.001"),
        price=None,
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="test-order-1",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


def _limit(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Limit",
        quantity=Decimal("0.001"),
        price=Decimal("42000.50"),
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="test-order-2",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


def _builder() -> BybitCreateOrderPayloadBuilder:
    return BybitCreateOrderPayloadBuilder()


# ---------------------------------------------------------------------------
# 1. Import and public API
# ---------------------------------------------------------------------------

class TestImport:
    def test_class_importable_from_module(self):
        assert BybitCreateOrderPayloadBuilder is not None

    def test_instance_creatable_with_no_args(self):
        b = BybitCreateOrderPayloadBuilder()
        assert b is not None

    def test_has_build_method(self):
        b = _builder()
        assert hasattr(b, "build")
        assert callable(b.build)

    def test_no_extra_public_methods(self):
        b = _builder()
        expected = {"build"}
        actual = {n for n in dir(b) if not n.startswith("_")}
        assert actual == expected


# ---------------------------------------------------------------------------
# 2. Input validation
# ---------------------------------------------------------------------------

class TestInputValidation:
    def test_rejects_none_request(self):
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            _builder().build(request=None)

    def test_rejects_str_request(self):
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            _builder().build(request="BTCUSDT")

    def test_rejects_dict_request(self):
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            _builder().build(request={"symbol": "BTCUSDT"})

    def test_rejects_int_request(self):
        with pytest.raises(TypeError, match="request must be BybitCreateOrderRequest"):
            _builder().build(request=42)

    def test_build_is_keyword_only(self):
        b = _builder()
        r = _market()
        with pytest.raises(TypeError):
            b.build(r)


# ---------------------------------------------------------------------------
# 3. Market payload — keys, values, and order
# ---------------------------------------------------------------------------

class TestMarketPayload:
    def test_returns_dict(self):
        result = _builder().build(request=_market())
        assert isinstance(result, dict)

    def test_market_has_exactly_8_keys(self):
        result = _builder().build(request=_market())
        assert len(result) == 8

    def test_market_key_order(self):
        result = _builder().build(request=_market())
        assert list(result.keys()) == [
            "category",
            "symbol",
            "side",
            "orderType",
            "qty",
            "timeInForce",
            "reduceOnly",
            "orderLinkId",
        ]

    def test_market_category_is_linear(self):
        result = _builder().build(request=_market())
        assert result["category"] == "linear"

    def test_market_symbol_correct(self):
        result = _builder().build(request=_market(symbol="ETHUSDT"))
        assert result["symbol"] == "ETHUSDT"

    def test_market_side_buy(self):
        result = _builder().build(request=_market(side="Buy"))
        assert result["side"] == "Buy"

    def test_market_side_sell(self):
        result = _builder().build(request=_market(side="Sell"))
        assert result["side"] == "Sell"

    def test_market_order_type_key(self):
        result = _builder().build(request=_market())
        assert "orderType" in result

    def test_market_order_type_value(self):
        result = _builder().build(request=_market())
        assert result["orderType"] == "Market"

    def test_market_qty_is_str(self):
        result = _builder().build(request=_market())
        assert isinstance(result["qty"], str)

    def test_market_no_price_key(self):
        result = _builder().build(request=_market())
        assert "price" not in result

    def test_market_time_in_force_key(self):
        result = _builder().build(request=_market())
        assert "timeInForce" in result

    def test_market_time_in_force_value(self):
        result = _builder().build(request=_market(time_in_force="IOC"))
        assert result["timeInForce"] == "IOC"

    def test_market_reduce_only_false(self):
        result = _builder().build(request=_market(reduce_only=False))
        assert result["reduceOnly"] is False

    def test_market_reduce_only_true(self):
        result = _builder().build(request=_market(reduce_only=True))
        assert result["reduceOnly"] is True

    def test_market_order_link_id_key(self):
        result = _builder().build(request=_market())
        assert "orderLinkId" in result

    def test_market_order_link_id_value(self):
        result = _builder().build(request=_market(order_link_id="my-link-id"))
        assert result["orderLinkId"] == "my-link-id"


# ---------------------------------------------------------------------------
# 4. Limit payload — keys, values, and order
# ---------------------------------------------------------------------------

class TestLimitPayload:
    def test_returns_dict(self):
        result = _builder().build(request=_limit())
        assert isinstance(result, dict)

    def test_limit_has_exactly_9_keys(self):
        result = _builder().build(request=_limit())
        assert len(result) == 9

    def test_limit_key_order(self):
        result = _builder().build(request=_limit())
        assert list(result.keys()) == [
            "category",
            "symbol",
            "side",
            "orderType",
            "qty",
            "price",
            "timeInForce",
            "reduceOnly",
            "orderLinkId",
        ]

    def test_limit_category_is_linear(self):
        result = _builder().build(request=_limit())
        assert result["category"] == "linear"

    def test_limit_order_type_value(self):
        result = _builder().build(request=_limit())
        assert result["orderType"] == "Limit"

    def test_limit_has_price_key(self):
        result = _builder().build(request=_limit())
        assert "price" in result

    def test_limit_price_is_str(self):
        result = _builder().build(request=_limit())
        assert isinstance(result["price"], str)

    def test_limit_price_value(self):
        result = _builder().build(request=_limit(price=Decimal("42000.50")))
        assert result["price"] == "42000.50"

    def test_limit_price_between_qty_and_time_in_force(self):
        keys = list(_builder().build(request=_limit()).keys())
        qty_idx = keys.index("qty")
        price_idx = keys.index("price")
        tif_idx = keys.index("timeInForce")
        assert qty_idx < price_idx < tif_idx

    def test_limit_reduce_only_false(self):
        result = _builder().build(request=_limit(reduce_only=False))
        assert result["reduceOnly"] is False

    def test_limit_reduce_only_true(self):
        result = _builder().build(request=_limit(reduce_only=True))
        assert result["reduceOnly"] is True

    def test_limit_time_in_force_post_only(self):
        result = _builder().build(request=_limit(time_in_force="PostOnly"))
        assert result["timeInForce"] == "PostOnly"


# ---------------------------------------------------------------------------
# 5. Decimal-to-str conversion
# ---------------------------------------------------------------------------

class TestDecimalConversion:
    def test_market_qty_str_conversion(self):
        result = _builder().build(request=_market(quantity=Decimal("0.001")))
        assert result["qty"] == "0.001"

    def test_market_qty_large_value(self):
        result = _builder().build(request=_market(quantity=Decimal("10.5")))
        assert result["qty"] == "10.5"

    def test_market_qty_integer_decimal(self):
        result = _builder().build(request=_market(quantity=Decimal("1")))
        assert result["qty"] == "1"

    def test_market_qty_small_decimal(self):
        qty = Decimal("0.00000001")
        result = _builder().build(request=_market(quantity=qty))
        assert result["qty"] == "0.00000001"

    def test_market_qty_exponential_input_rendered_plain(self):
        qty = Decimal("1E-8")
        result = _builder().build(request=_market(quantity=qty))
        assert result["qty"] == "0.00000001"
        assert "E" not in result["qty"]
        assert "e" not in result["qty"]

    def test_market_qty_large_exponential_input_rendered_plain(self):
        qty = Decimal("1E+16")
        result = _builder().build(request=_market(quantity=qty))
        assert result["qty"] == "10000000000000000"
        assert "E" not in result["qty"]

    def test_limit_qty_str_conversion(self):
        result = _builder().build(request=_limit(quantity=Decimal("2.5")))
        assert result["qty"] == "2.5"

    def test_limit_price_str_conversion(self):
        result = _builder().build(request=_limit(price=Decimal("30000.00")))
        assert result["price"] == "30000.00"

    def test_limit_price_high_precision(self):
        result = _builder().build(request=_limit(price=Decimal("99999.999")))
        assert result["price"] == "99999.999"

    def test_limit_price_round_number(self):
        result = _builder().build(request=_limit(price=Decimal("50000")))
        assert result["price"] == "50000"

    def test_qty_is_str_not_float(self):
        result = _builder().build(request=_market(quantity=Decimal("0.1")))
        assert isinstance(result["qty"], str)
        assert not isinstance(result["qty"], float)


# ---------------------------------------------------------------------------
# 6. Value conservation
# ---------------------------------------------------------------------------

class TestValueConservation:
    def test_symbol_preserved_exactly(self):
        result = _builder().build(request=_market(symbol="XAUTUSDT"))
        assert result["symbol"] == "XAUTUSDT"

    def test_side_preserved_exactly(self):
        result = _builder().build(request=_market(side="Sell"))
        assert result["side"] == "Sell"

    def test_time_in_force_fok(self):
        result = _builder().build(request=_market(time_in_force="FOK"))
        assert result["timeInForce"] == "FOK"

    def test_time_in_force_gtc(self):
        result = _builder().build(request=_limit(time_in_force="GTC"))
        assert result["timeInForce"] == "GTC"

    def test_order_link_id_preserved_exactly(self):
        lid = "abc-123-def-456"
        result = _builder().build(request=_market(order_link_id=lid))
        assert result["orderLinkId"] == lid

    def test_reduce_only_type_is_bool_not_int_false(self):
        result = _builder().build(request=_market(reduce_only=False))
        assert result["reduceOnly"] is False
        assert type(result["reduceOnly"]) is bool

    def test_reduce_only_type_is_bool_not_int_true(self):
        result = _builder().build(request=_limit(reduce_only=True))
        assert result["reduceOnly"] is True
        assert type(result["reduceOnly"]) is bool


# ---------------------------------------------------------------------------
# 7. New dict per call
# ---------------------------------------------------------------------------

class TestNewDictPerCall:
    def test_each_call_returns_new_dict(self):
        b = _builder()
        r = _market()
        p1 = b.build(request=r)
        p2 = b.build(request=r)
        assert p1 is not p2

    def test_modifying_result_does_not_affect_next_call(self):
        b = _builder()
        r = _market(symbol="BTCUSDT")
        p1 = b.build(request=r)
        p1["symbol"] = "MODIFIED"
        p2 = b.build(request=r)
        assert p2["symbol"] == "BTCUSDT"

    def test_two_different_requests_return_independent_dicts(self):
        b = _builder()
        r1 = _market(symbol="BTCUSDT")
        r2 = _market(symbol="ETHUSDT")
        p1 = b.build(request=r1)
        p2 = b.build(request=r2)
        assert p1["symbol"] == "BTCUSDT"
        assert p2["symbol"] == "ETHUSDT"

    def test_no_last_payload_stored_on_builder(self):
        b = _builder()
        r = _market()
        b.build(request=r)
        assert not hasattr(b, "last_payload")
        assert not hasattr(b, "_last_payload")
        assert not hasattr(b, "cache")

    def test_market_and_limit_can_be_built_with_same_builder(self):
        b = _builder()
        pm = b.build(request=_market())
        pl = b.build(request=_limit())
        assert "price" not in pm
        assert "price" in pl


# ---------------------------------------------------------------------------
# 8. No extra fields
# ---------------------------------------------------------------------------

class TestNoExtraFields:
    def test_market_exact_keys(self):
        result = _builder().build(request=_market())
        assert set(result.keys()) == {
            "category",
            "symbol",
            "side",
            "orderType",
            "qty",
            "timeInForce",
            "reduceOnly",
            "orderLinkId",
        }

    def test_limit_exact_keys(self):
        result = _builder().build(request=_limit())
        assert set(result.keys()) == {
            "category",
            "symbol",
            "side",
            "orderType",
            "qty",
            "price",
            "timeInForce",
            "reduceOnly",
            "orderLinkId",
        }

    def test_no_category_snake_case(self):
        result = _builder().build(request=_market())
        assert "category" in result
        assert "category_linear" not in result

    def test_no_raw_quantity_field(self):
        result = _builder().build(request=_market())
        assert "quantity" not in result

    def test_no_raw_price_field_in_limit(self):
        result = _builder().build(request=_limit())
        assert "price" in result
        assert "raw_price" not in result

    def test_no_raw_order_type(self):
        result = _builder().build(request=_market())
        assert "order_type" not in result

    def test_no_raw_time_in_force(self):
        result = _builder().build(request=_market())
        assert "time_in_force" not in result

    def test_no_raw_reduce_only(self):
        result = _builder().build(request=_market())
        assert "reduce_only" not in result

    def test_no_raw_order_link_id(self):
        result = _builder().build(request=_market())
        assert "order_link_id" not in result


# ---------------------------------------------------------------------------
# 9. No extra responsibilities
# ---------------------------------------------------------------------------

class TestNoExtraResponsibilities:
    def test_no_json_serialization(self):
        result = _builder().build(request=_market())
        assert isinstance(result, dict)
        assert not isinstance(result, str)

    def test_no_http_call_on_build(self):
        # Build must return synchronously without network IO
        import socket
        original_connect = socket.socket.connect

        calls = []

        def patched_connect(self, *args, **kwargs):
            calls.append(args)
            return original_connect(self, *args, **kwargs)

        socket.socket.connect = patched_connect
        try:
            _builder().build(request=_market())
        finally:
            socket.socket.connect = original_connect

        assert calls == [], "build() must not make any network calls"

    def test_builder_has_no_state_after_instantiation(self):
        b = _builder()
        instance_vars = {k for k in vars(b)}
        assert instance_vars == set()

    def test_request_is_not_modified_by_build(self):
        r = _market(symbol="BTCUSDT", quantity=Decimal("0.001"))
        _builder().build(request=r)
        assert r.symbol == "BTCUSDT"
        assert r.quantity == Decimal("0.001")
