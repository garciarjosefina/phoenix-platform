import os
import pytest
from decimal import Decimal
import execution_gateway
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest


# ── helpers ────────────────────────────────────────────────────────────────

def _market(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Market",
        quantity=Decimal("0.001"),
        price=None,
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="bot_order_001",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


def _limit(**kwargs) -> BybitCreateOrderRequest:
    defaults = dict(
        symbol="BTCUSDT",
        side="Buy",
        order_type="Limit",
        quantity=Decimal("0.001"),
        price=Decimal("50000.00"),
        time_in_force="GTC",
        reduce_only=False,
        order_link_id="bot_order_001",
    )
    return BybitCreateOrderRequest(**{**defaults, **kwargs})


# ── import & public API ────────────────────────────────────────────────────

class TestImport:
    def test_direct_import(self):
        from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest as R
        assert R is BybitCreateOrderRequest

    def test_public_import(self):
        assert hasattr(execution_gateway, "BybitCreateOrderRequest")
        assert execution_gateway.BybitCreateOrderRequest is BybitCreateOrderRequest

    def test_in_all(self):
        assert "BybitCreateOrderRequest" in execution_gateway.__all__


# ── construcción válida ────────────────────────────────────────────────────

class TestValidConstruction:
    def test_market_buy(self):
        r = _market(side="Buy")
        assert r.side == "Buy"
        assert r.order_type == "Market"
        assert r.price is None

    def test_market_sell(self):
        r = _market(side="Sell")
        assert r.side == "Sell"
        assert r.order_type == "Market"

    def test_limit_buy(self):
        r = _limit(side="Buy")
        assert r.side == "Buy"
        assert r.order_type == "Limit"
        assert r.price == Decimal("50000.00")

    def test_limit_sell(self):
        r = _limit(side="Sell")
        assert r.side == "Sell"
        assert r.order_type == "Limit"

    def test_all_values_preserved(self):
        qty = Decimal("0.001")
        r = _market(symbol="XAUTUSDT", quantity=qty)
        assert r.symbol == "XAUTUSDT"
        assert r.quantity is qty

    def test_price_none_in_market(self):
        r = _market(price=None)
        assert r.price is None

    def test_price_decimal_in_limit(self):
        price = Decimal("50000.00")
        r = _limit(price=price)
        assert r.price is price

    def test_reduce_only_true(self):
        r = _market(reduce_only=True)
        assert r.reduce_only is True

    def test_reduce_only_false(self):
        r = _market(reduce_only=False)
        assert r.reduce_only is False


# ── symbol ─────────────────────────────────────────────────────────────────

class TestSymbol:
    def test_accepts_valid_symbol(self):
        r = _market(symbol="BTCUSDT")
        assert r.symbol == "BTCUSDT"

    def test_rejects_non_str_symbol(self):
        with pytest.raises(TypeError):
            _market(symbol=123)

    def test_rejects_none_symbol(self):
        with pytest.raises(TypeError):
            _market(symbol=None)

    def test_rejects_empty_symbol(self):
        with pytest.raises(ValueError):
            _market(symbol="")

    def test_rejects_whitespace_symbol(self):
        with pytest.raises(ValueError):
            _market(symbol="   ")

    def test_preserves_symbol_exactly(self):
        r = _market(symbol="XAUTUSDT")
        assert r.symbol == "XAUTUSDT"

    def test_no_upper_conversion(self):
        r = _market(symbol="btcusdt")
        assert r.symbol == "btcusdt"

    def test_no_strip(self):
        r = _market(symbol="  BTCUSDT  ")
        assert r.symbol == "  BTCUSDT  "

    def test_no_symbol_list_validation(self):
        r = _market(symbol="FAKESYMBOL")
        assert r.symbol == "FAKESYMBOL"


# ── side ───────────────────────────────────────────────────────────────────

class TestSide:
    def test_accepts_buy(self):
        r = _market(side="Buy")
        assert r.side == "Buy"

    def test_accepts_sell(self):
        r = _market(side="Sell")
        assert r.side == "Sell"

    def test_rejects_non_str_side(self):
        with pytest.raises(TypeError):
            _market(side=1)

    def test_rejects_none_side(self):
        with pytest.raises(TypeError):
            _market(side=None)

    def test_rejects_lowercase_buy(self):
        with pytest.raises(ValueError):
            _market(side="buy")

    def test_rejects_lowercase_sell(self):
        with pytest.raises(ValueError):
            _market(side="sell")

    def test_rejects_uppercase_buy(self):
        with pytest.raises(ValueError):
            _market(side="BUY")

    def test_rejects_uppercase_sell(self):
        with pytest.raises(ValueError):
            _market(side="SELL")

    def test_rejects_long(self):
        with pytest.raises(ValueError):
            _market(side="Long")

    def test_rejects_short(self):
        with pytest.raises(ValueError):
            _market(side="Short")

    def test_no_normalization(self):
        with pytest.raises(ValueError):
            _market(side="buy")


# ── order_type ─────────────────────────────────────────────────────────────

class TestOrderType:
    def test_accepts_market(self):
        r = _market(order_type="Market")
        assert r.order_type == "Market"

    def test_accepts_limit(self):
        r = _limit(order_type="Limit")
        assert r.order_type == "Limit"

    def test_rejects_non_str_order_type(self):
        with pytest.raises(TypeError):
            _market(order_type=0)

    def test_rejects_none_order_type(self):
        with pytest.raises(TypeError):
            _market(order_type=None)

    def test_rejects_lowercase_market(self):
        with pytest.raises(ValueError):
            _market(order_type="market")

    def test_rejects_lowercase_limit(self):
        with pytest.raises(ValueError):
            _market(order_type="limit", price=Decimal("1"))

    def test_rejects_unknown_order_type(self):
        with pytest.raises(ValueError):
            _market(order_type="Stop")

    def test_no_normalization(self):
        with pytest.raises(ValueError):
            _market(order_type="MARKET")


# ── quantity ───────────────────────────────────────────────────────────────

class TestQuantity:
    def test_accepts_decimal_positive(self):
        qty = Decimal("0.001")
        r = _market(quantity=qty)
        assert r.quantity == qty

    def test_rejects_int(self):
        with pytest.raises(TypeError):
            _market(quantity=1)

    def test_rejects_float(self):
        with pytest.raises(TypeError):
            _market(quantity=0.001)

    def test_rejects_str(self):
        with pytest.raises(TypeError):
            _market(quantity="0.001")

    def test_rejects_bool(self):
        with pytest.raises(TypeError):
            _market(quantity=True)

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            _market(quantity=None)

    def test_rejects_zero(self):
        with pytest.raises(ValueError):
            _market(quantity=Decimal("0"))

    def test_rejects_negative(self):
        with pytest.raises(ValueError):
            _market(quantity=Decimal("-0.001"))

    def test_no_rounding(self):
        qty = Decimal("0.00000001")
        r = _market(quantity=qty)
        assert r.quantity == qty

    def test_preserves_exact_value(self):
        qty = Decimal("1.23456789")
        r = _market(quantity=qty)
        assert r.quantity is qty


# ── price ──────────────────────────────────────────────────────────────────

class TestPrice:
    def test_market_accepts_none(self):
        r = _market(price=None)
        assert r.price is None

    def test_market_rejects_decimal(self):
        with pytest.raises(ValueError):
            _market(price=Decimal("50000"))

    def test_limit_requires_decimal(self):
        price = Decimal("50000.00")
        r = _limit(price=price)
        assert r.price is price

    def test_limit_rejects_none(self):
        with pytest.raises(ValueError):
            _limit(price=None)

    def test_rejects_int_price(self):
        with pytest.raises(TypeError):
            _limit(price=50000)

    def test_rejects_float_price(self):
        with pytest.raises(TypeError):
            _limit(price=50000.0)

    def test_rejects_str_price(self):
        with pytest.raises(TypeError):
            _limit(price="50000")

    def test_rejects_bool_price(self):
        with pytest.raises(TypeError):
            _limit(price=True)

    def test_rejects_zero_price(self):
        with pytest.raises(ValueError):
            _limit(price=Decimal("0"))

    def test_rejects_negative_price(self):
        with pytest.raises(ValueError):
            _limit(price=Decimal("-1"))

    def test_no_rounding(self):
        price = Decimal("50000.123456789")
        r = _limit(price=price)
        assert r.price == price

    def test_preserves_exact_value(self):
        price = Decimal("49999.99")
        r = _limit(price=price)
        assert r.price is price


# ── time_in_force ──────────────────────────────────────────────────────────

class TestTimeInForce:
    def test_accepts_gtc(self):
        r = _market(time_in_force="GTC")
        assert r.time_in_force == "GTC"

    def test_accepts_ioc(self):
        r = _market(time_in_force="IOC")
        assert r.time_in_force == "IOC"

    def test_accepts_fok(self):
        r = _market(time_in_force="FOK")
        assert r.time_in_force == "FOK"

    def test_accepts_postonly(self):
        r = _limit(time_in_force="PostOnly")
        assert r.time_in_force == "PostOnly"

    def test_rejects_non_str(self):
        with pytest.raises(TypeError):
            _market(time_in_force=0)

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            _market(time_in_force=None)

    def test_rejects_lowercase(self):
        with pytest.raises(ValueError):
            _market(time_in_force="gtc")

    def test_rejects_uppercase_postonly(self):
        with pytest.raises(ValueError):
            _market(time_in_force="POSTONLY")

    def test_rejects_unknown(self):
        with pytest.raises(ValueError):
            _market(time_in_force="DAY")

    def test_no_normalization(self):
        with pytest.raises(ValueError):
            _market(time_in_force="ioc")

    def test_no_extra_rules_by_order_type(self):
        r = _market(time_in_force="PostOnly")
        assert r.time_in_force == "PostOnly"


# ── reduce_only ────────────────────────────────────────────────────────────

class TestReduceOnly:
    def test_accepts_true(self):
        r = _market(reduce_only=True)
        assert r.reduce_only is True

    def test_accepts_false(self):
        r = _market(reduce_only=False)
        assert r.reduce_only is False

    def test_rejects_int_zero(self):
        with pytest.raises(TypeError):
            _market(reduce_only=0)

    def test_rejects_int_one(self):
        with pytest.raises(TypeError):
            _market(reduce_only=1)

    def test_rejects_str(self):
        with pytest.raises(TypeError):
            _market(reduce_only="True")

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            _market(reduce_only=None)


# ── order_link_id ──────────────────────────────────────────────────────────

class TestOrderLinkId:
    def test_accepts_valid(self):
        r = _market(order_link_id="bot_order_001")
        assert r.order_link_id == "bot_order_001"

    def test_accepts_exactly_36_chars(self):
        link_id = "a" * 36
        r = _market(order_link_id=link_id)
        assert r.order_link_id == link_id

    def test_rejects_non_str(self):
        with pytest.raises(TypeError):
            _market(order_link_id=123)

    def test_rejects_none(self):
        with pytest.raises(TypeError):
            _market(order_link_id=None)

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            _market(order_link_id="")

    def test_rejects_whitespace_only(self):
        with pytest.raises(ValueError):
            _market(order_link_id="   ")

    def test_rejects_37_chars(self):
        with pytest.raises(ValueError):
            _market(order_link_id="a" * 37)

    def test_preserves_exactly(self):
        link_id = "bot_abc_001"
        r = _market(order_link_id=link_id)
        assert r.order_link_id == link_id

    def test_no_strip(self):
        r = _market(order_link_id="  id  ")
        assert r.order_link_id == "  id  "

    def test_no_uuid_required(self):
        r = _market(order_link_id="simple_id")
        assert r.order_link_id == "simple_id"

    def test_no_prefix_required(self):
        r = _market(order_link_id="any_prefix_is_fine")
        assert r.order_link_id == "any_prefix_is_fine"

    def test_no_uniqueness_check(self):
        r1 = _market(order_link_id="same_id")
        r2 = _market(order_link_id="same_id")
        assert r1.order_link_id == r2.order_link_id


# ── inmutabilidad ──────────────────────────────────────────────────────────

class TestImmutability:
    def test_is_frozen_dataclass(self):
        from dataclasses import is_dataclass
        assert is_dataclass(BybitCreateOrderRequest)

    def test_equality_by_value(self):
        a = _market()
        b = _market()
        assert a == b

    def test_rejects_mutation_symbol(self):
        r = _market()
        with pytest.raises(Exception):
            r.symbol = "ETHUSDT"

    def test_rejects_mutation_side(self):
        r = _market()
        with pytest.raises(Exception):
            r.side = "Sell"

    def test_rejects_mutation_order_type(self):
        r = _market()
        with pytest.raises(Exception):
            r.order_type = "Limit"

    def test_rejects_mutation_quantity(self):
        r = _market()
        with pytest.raises(Exception):
            r.quantity = Decimal("1")

    def test_rejects_mutation_price(self):
        r = _market()
        with pytest.raises(Exception):
            r.price = Decimal("1")

    def test_rejects_mutation_reduce_only(self):
        r = _market()
        with pytest.raises(Exception):
            r.reduce_only = True


# ── ausencia de comportamiento adicional ───────────────────────────────────

class TestNoBehavior:
    def test_no_to_payload(self):
        r = _market()
        assert not hasattr(r, "to_payload")

    def test_no_to_dict(self):
        r = _market()
        assert not hasattr(r, "to_dict")

    def test_no_serialize(self):
        r = _market()
        assert not hasattr(r, "serialize")

    def test_no_endpoint(self):
        r = _market()
        assert not hasattr(r, "endpoint")

    def test_no_category(self):
        r = _market()
        assert not hasattr(r, "category")

    def test_no_is_market(self):
        r = _market()
        assert not hasattr(r, "is_market")

    def test_no_is_limit(self):
        r = _market()
        assert not hasattr(r, "is_limit")

    def test_no_notional(self):
        r = _market()
        assert not hasattr(r, "notional")

    def test_no_extra_public_methods(self):
        import dataclasses
        r = _market()
        field_names = {f.name for f in dataclasses.fields(r)}
        actual_public = {n for n in dir(r) if not n.startswith("_")}
        assert actual_public == field_names

    def test_no_executor_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "BybitEndpointExecutor")

    def test_no_api_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "BybitPrivateApi")

    def test_no_sender_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "BybitPrivateRequestSender")

    def test_no_transport_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "HttpTransport")
        assert not hasattr(m, "UrllibHttpTransport")

    def test_no_authenticator_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "BybitAuthenticator")

    def test_no_serializer_imported(self):
        import execution_gateway.bybit_create_order_request as m
        assert not hasattr(m, "JsonSerializer")

    def test_no_base_url_in_module(self):
        import inspect
        import execution_gateway.bybit_create_order_request as m
        src = inspect.getsource(m)
        assert "bybit.com" not in src
        assert "https://" not in src

    def test_no_camelcase_keys(self):
        import inspect
        import execution_gateway.bybit_create_order_request as m
        src = inspect.getsource(m)
        assert "orderType" not in src
        assert "timeInForce" not in src
        assert "reduceOnly" not in src
        assert "orderLinkId" not in src

    def test_no_linear_category(self):
        import inspect
        import execution_gateway.bybit_create_order_request as m
        src = inspect.getsource(m)
        assert "linear" not in src

    def test_no_env_read(self):
        os.environ["BYBIT_API_KEY"] = "__sentinel__"
        try:
            r = _market()
            assert r is not None
        finally:
            del os.environ["BYBIT_API_KEY"]

    def test_existing_suite_unaffected(self):
        from execution_gateway.config import GatewayConfig
        from execution_gateway.bybit_endpoints import BYBIT_CREATE_ORDER_ENDPOINT
        assert GatewayConfig().environment == "demo"
        assert BYBIT_CREATE_ORDER_ENDPOINT.method == "POST"
