import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.observed_order_economics_contracts import ObservedOrderEconomics

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


def _economics(**overrides):
    defaults = dict(
        execution_order_id=_OID, symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("1"), price=Decimal("100"), reduce_only=False,
    )
    defaults.update(overrides)
    return ObservedOrderEconomics(**defaults)


class TestImport:
    @pytest.mark.parametrize("name", ["ObservedOrderEconomics"])
    def test_importable_from_package_and_in_all(self, name):
        assert hasattr(execution_gateway, name)
        assert name in execution_gateway.__all__


class TestConstruction:
    def test_constructs_validly(self):
        ev = _economics()
        assert ev.execution_order_id is _OID
        assert ev.symbol == "BTCUSDT"
        assert ev.side == "buy"
        assert ev.order_type == "limit"
        assert ev.quantity == Decimal("1")
        assert ev.price == Decimal("100")
        assert ev.reduce_only is False

    def test_is_frozen(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            _economics().symbol = "ETHUSDT"


class TestExecutionOrderId:
    def test_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "b" * 32)
        assert _economics(execution_order_id=marker).execution_order_id is marker

    @pytest.mark.parametrize("bad", [None, "ord_" + "a" * 32, 123, True, 1.5, b"x", object()])
    def test_rejects_non_execution_order_id(self, bad):
        with pytest.raises(TypeError):
            _economics(execution_order_id=bad)

    def test_rejects_duck_typed_fake_with_value_attribute(self):
        class _Fake:
            value = "ord_" + "c" * 32
        with pytest.raises(TypeError):
            _economics(execution_order_id=_Fake())


class TestSymbol:
    @pytest.mark.parametrize("bad", [None, 1, 1.5, True, [], {}, object()])
    def test_rejects_non_str(self, bad):
        with pytest.raises(TypeError):
            _economics(symbol=bad)

    @pytest.mark.parametrize("bad", ["", "   "])
    def test_rejects_empty_or_whitespace(self, bad):
        with pytest.raises(ValueError):
            _economics(symbol=bad)

    def test_preserved_literal_no_normalization(self):
        assert _economics(symbol="btcusdt").symbol == "btcusdt"


class TestSide:
    @pytest.mark.parametrize("side", ["buy", "sell"])
    def test_accepts_valid(self, side):
        assert _economics(side=side).side == side

    @pytest.mark.parametrize("bad", ["Buy", "SELL", "long", "", None, 1, True])
    def test_rejects_invalid(self, bad):
        with pytest.raises((TypeError, ValueError)):
            _economics(side=bad)


class TestOrderType:
    @pytest.mark.parametrize("order_type,price", [("limit", Decimal("100")), ("market", None)])
    def test_accepts_valid(self, order_type, price):
        assert _economics(order_type=order_type, price=price).order_type == order_type

    @pytest.mark.parametrize("bad", ["Limit", "MARKET", "stop", "", None, 1, True])
    def test_rejects_invalid(self, bad):
        with pytest.raises((TypeError, ValueError)):
            _economics(order_type=bad, price=None)


class TestQuantity:
    @pytest.mark.parametrize("bad", [None, 1, 1.5, True, "1", [], {}, object()])
    def test_rejects_non_decimal(self, bad):
        with pytest.raises(TypeError):
            _economics(quantity=bad)

    @pytest.mark.parametrize("bad", [Decimal("0"), Decimal("-1")])
    def test_rejects_non_positive(self, bad):
        with pytest.raises(ValueError):
            _economics(quantity=bad)

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
    def test_rejects_non_finite(self, bad):
        with pytest.raises(ValueError):
            _economics(quantity=bad)

    def test_accepts_non_diadic_decimal(self):
        assert _economics(quantity=Decimal("0.1")).quantity == Decimal("0.1")


class TestPrice:
    def test_market_forbids_price(self):
        with pytest.raises(ValueError):
            _economics(order_type="market", price=Decimal("100"))

    def test_limit_requires_price(self):
        with pytest.raises(ValueError):
            _economics(order_type="limit", price=None)

    def test_market_price_none_is_valid(self):
        assert _economics(order_type="market", price=None).price is None

    @pytest.mark.parametrize("bad", [Decimal("0"), Decimal("-1")])
    def test_rejects_non_positive_price(self, bad):
        with pytest.raises(ValueError):
            _economics(price=bad)

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
    def test_rejects_non_finite_price(self, bad):
        with pytest.raises(ValueError):
            _economics(price=bad)

    @pytest.mark.parametrize("bad", [1, 1.5, "100", True, object()])
    def test_rejects_non_decimal_price_when_present(self, bad):
        with pytest.raises(TypeError):
            _economics(price=bad)


class TestReduceOnly:
    @pytest.mark.parametrize("value", [True, False])
    def test_accepts_bool(self, value):
        assert _economics(reduce_only=value).reduce_only is value

    @pytest.mark.parametrize("bad", [0, 1, None, "false", "true", [], {}])
    def test_rejects_non_bool(self, bad):
        with pytest.raises(TypeError):
            _economics(reduce_only=bad)


class TestExactFieldSet:
    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(ObservedOrderEconomics)}
        assert names == {
            "execution_order_id", "symbol", "side", "order_type",
            "quantity", "price", "reduce_only",
        }

    def test_no_metadata_or_evolution_fields(self):
        names = {f.name for f in dataclasses.fields(ObservedOrderEconomics)}
        for forbidden in (
            "exchange_order_id", "filled_quantity", "filled_value", "average_price",
            "remote_status", "cancel_type", "reject_reason", "remote_created_time_ms",
            "remote_updated_time_ms", "server_time_ms",
        ):
            assert forbidden not in names
