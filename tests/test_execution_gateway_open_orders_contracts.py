import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.open_orders_contracts import ExecutionOpenOrder, OpenOrdersSnapshot


def _order(**overrides):
    defaults = dict(
        exchange_order_id="bybit-order-1",
        order_id="phoenix-order-1",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity=Decimal("0.5"),
        price=Decimal("60000.5"),
        filled_quantity=Decimal("0"),
        status="new",
        reduce_only=False,
    )
    defaults.update(overrides)
    return ExecutionOpenOrder(**defaults)


class TestImport:
    def test_execution_open_order_importable_from_package(self):
        assert hasattr(execution_gateway, "ExecutionOpenOrder")
        assert execution_gateway.ExecutionOpenOrder is ExecutionOpenOrder

    def test_execution_open_order_in_all(self):
        assert "ExecutionOpenOrder" in execution_gateway.__all__

    def test_open_orders_snapshot_importable_from_package(self):
        assert hasattr(execution_gateway, "OpenOrdersSnapshot")
        assert execution_gateway.OpenOrdersSnapshot is OpenOrdersSnapshot

    def test_open_orders_snapshot_in_all(self):
        assert "OpenOrdersSnapshot" in execution_gateway.__all__


class TestExecutionOpenOrderContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExecutionOpenOrder)
        assert ExecutionOpenOrder.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExecutionOpenOrder)]
        assert names == [
            "exchange_order_id", "symbol", "side", "order_type", "quantity",
            "filled_quantity", "status", "reduce_only", "order_id", "price",
        ]

    def test_cannot_reassign_field(self):
        order = _order()
        with pytest.raises(Exception):
            order.status = "partially_filled"

    def test_no_bybit_types_in_public_attributes(self):
        order = _order()
        public = {k for k in vars(order) if not k.startswith("_")}
        forbidden = {"ret_code", "ret_msg", "result", "orderId", "orderLinkId", "orderStatus", "cumExecQty", "reduceOnly"}
        assert public.isdisjoint(forbidden)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _order(ret_code=0)

    # ── identidad dual ──────────────────────────────────────────────────

    def test_exchange_order_id_must_be_str(self):
        with pytest.raises(TypeError, match="exchange_order_id must be str"):
            _order(exchange_order_id=1)

    def test_exchange_order_id_must_not_be_empty(self):
        with pytest.raises(ValueError, match="exchange_order_id must not be empty"):
            _order(exchange_order_id="")

    def test_exchange_order_id_always_required_no_default(self):
        with pytest.raises(TypeError):
            ExecutionOpenOrder(
                symbol="BTCUSDT", side="buy", order_type="limit", quantity=Decimal("1"),
                filled_quantity=Decimal("0"), status="new", reduce_only=False,
            )

    def test_order_id_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionOpenOrder) if f.name == "order_id")
        assert field.default is None

    def test_order_id_none_is_valid_orphan_representation(self):
        order = _order(order_id=None)
        assert order.order_id is None

    def test_order_id_must_be_str_when_present(self):
        with pytest.raises(TypeError, match="order_id must be str or None"):
            _order(order_id=1)

    def test_order_id_must_not_be_empty_when_present(self):
        with pytest.raises(ValueError, match="order_id must not be empty"):
            _order(order_id="")

    def test_order_id_and_exchange_order_id_never_conflated(self):
        order = _order(order_id="domain-id", exchange_order_id="bybit-id")
        assert order.order_id == "domain-id"
        assert order.exchange_order_id == "bybit-id"
        assert order.order_id != order.exchange_order_id

    # ── symbol / side / order_type ──────────────────────────────────────

    def test_symbol_must_be_str(self):
        with pytest.raises(TypeError, match="symbol must be str"):
            _order(symbol=123)

    def test_symbol_must_not_be_empty(self):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            _order(symbol="")

    def test_side_accepts_buy(self):
        assert _order(side="buy").side == "buy"

    def test_side_accepts_sell(self):
        assert _order(side="sell").side == "sell"

    def test_side_rejects_capitalized_bybit_vocabulary(self):
        with pytest.raises(ValueError, match="side must be 'buy' or 'sell'"):
            _order(side="Buy")

    def test_order_type_accepts_limit(self):
        assert _order(order_type="limit").order_type == "limit"

    def test_order_type_accepts_market(self):
        assert _order(order_type="market", price=None).order_type == "market"

    def test_order_type_rejects_capitalized_bybit_vocabulary(self):
        with pytest.raises(ValueError, match="order_type must be 'market' or 'limit'"):
            _order(order_type="Limit")

    def test_order_type_rejects_unknown(self):
        with pytest.raises(ValueError, match="order_type must be 'market' or 'limit'"):
            _order(order_type="Conditional")

    # ── quantity / price / filled_quantity ───────────────────────────────

    def test_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _order(quantity=0.5)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity must be > 0"):
            _order(quantity=Decimal("0"))

    def test_quantity_rejects_nan(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _order(quantity=Decimal("nan"))

    def test_price_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionOpenOrder) if f.name == "price")
        assert field.default is None

    def test_price_none_valid_for_market_order(self):
        order = _order(order_type="market", price=None)
        assert order.price is None

    def test_price_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="price must be Decimal or None"):
            _order(price=60000.5)

    def test_price_must_be_positive_when_present(self):
        with pytest.raises(ValueError, match="price must be > 0"):
            _order(price=Decimal("0"))

    def test_price_rejects_nan(self):
        with pytest.raises(ValueError, match="price must be finite"):
            _order(price=Decimal("nan"))

    def test_filled_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="filled_quantity must be Decimal"):
            _order(filled_quantity=0.0)

    def test_filled_quantity_zero_is_valid(self):
        order = _order(filled_quantity=Decimal("0"))
        assert order.filled_quantity == Decimal("0")

    def test_filled_quantity_rejects_negative(self):
        with pytest.raises(ValueError, match="filled_quantity must be >= 0"):
            _order(filled_quantity=Decimal("-1"))

    def test_filled_quantity_rejects_nan(self):
        with pytest.raises(ValueError, match="filled_quantity must be finite"):
            _order(filled_quantity=Decimal("nan"))

    def test_filled_quantity_greater_than_quantity_not_enforced(self):
        # Deliberado: no se confirma que Bybit garantice cumExecQty <= qty
        # en todo momento para este endpoint -- no se impone una regla de
        # negocio no verificada (lección de la auditoría del Hito 3.70).
        order = _order(quantity=Decimal("1"), filled_quantity=Decimal("1.5"))
        assert order.filled_quantity == Decimal("1.5")

    # ── status ────────────────────────────────────────────────────────

    def test_status_accepts_new(self):
        assert _order(status="new").status == "new"

    def test_status_accepts_partially_filled(self):
        assert _order(status="partially_filled").status == "partially_filled"

    def test_status_accepts_untriggered(self):
        assert _order(status="untriggered").status == "untriggered"

    def test_status_rejects_capitalized_bybit_vocabulary(self):
        with pytest.raises(ValueError, match="status must be one of"):
            _order(status="New")

    def test_status_rejects_terminal_state(self):
        # Filled/Cancelled son estados terminales -- fuera del scope de
        # /v5/order/realtime, no deben aceptarse en este contrato.
        with pytest.raises(ValueError, match="status must be one of"):
            _order(status="filled")

    # ── reduce_only ───────────────────────────────────────────────────

    def test_reduce_only_accepts_true(self):
        assert _order(reduce_only=True).reduce_only is True

    def test_reduce_only_accepts_false(self):
        assert _order(reduce_only=False).reduce_only is False

    def test_reduce_only_rejects_string_true(self):
        with pytest.raises(TypeError, match="reduce_only must be bool"):
            _order(reduce_only="true")

    def test_reduce_only_rejects_int(self):
        with pytest.raises(TypeError, match="reduce_only must be bool"):
            _order(reduce_only=1)

    # ── superficie / repr / equality ──────────────────────────────────

    def test_repr_does_not_crash(self):
        text = repr(_order())
        assert "BTCUSDT" in text

    def test_equality_by_value(self):
        assert _order() == _order()

    def test_inequality_on_different_exchange_order_id(self):
        assert _order(exchange_order_id="a") != _order(exchange_order_id="b")


class TestOpenOrdersSnapshotContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(OpenOrdersSnapshot)
        assert OpenOrdersSnapshot.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(OpenOrdersSnapshot)]
        assert names == ["orders", "server_time_ms"]

    def test_empty_snapshot_is_valid(self):
        snapshot = OpenOrdersSnapshot(orders=(), server_time_ms=1_700_000_000_000)
        assert snapshot.orders == ()

    def test_orders_must_be_tuple(self):
        with pytest.raises(TypeError, match="orders must be tuple"):
            OpenOrdersSnapshot(orders=[_order()], server_time_ms=1)

    def test_orders_items_must_be_execution_open_order(self):
        with pytest.raises(TypeError, match="ExecutionOpenOrder"):
            OpenOrdersSnapshot(orders=({"symbol": "BTCUSDT"},), server_time_ms=1)

    def test_orders_preserved_in_order(self):
        o1 = _order(exchange_order_id="1")
        o2 = _order(exchange_order_id="2")
        snapshot = OpenOrdersSnapshot(orders=(o1, o2), server_time_ms=1)
        assert snapshot.orders == (o1, o2)

    def test_no_duplication_no_loss(self):
        items = tuple(_order(exchange_order_id=f"id-{i}") for i in range(5))
        snapshot = OpenOrdersSnapshot(orders=items, server_time_ms=1)
        assert len(snapshot.orders) == 5

    def test_server_time_ms_must_be_int(self):
        with pytest.raises(TypeError, match="server_time_ms must be int"):
            OpenOrdersSnapshot(orders=(), server_time_ms=1.5)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time_ms must be >= 0"):
            OpenOrdersSnapshot(orders=(), server_time_ms=-1)

    def test_cannot_reassign_orders(self):
        snapshot = OpenOrdersSnapshot(orders=(), server_time_ms=1)
        with pytest.raises(Exception):
            snapshot.orders = (_order(),)

    def test_no_bybit_types_in_public_attributes(self):
        snapshot = OpenOrdersSnapshot(orders=(), server_time_ms=1)
        public = {k for k in vars(snapshot) if not k.startswith("_")}
        assert public == {"orders", "server_time_ms"}
