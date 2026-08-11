import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.positions_contracts import ExecutionPosition, PositionsSnapshot


def _position(**overrides):
    defaults = dict(
        symbol="BTCUSDT",
        side="buy",
        quantity=Decimal("0.5"),
        entry_price=Decimal("60000.5"),
        leverage=Decimal("10"),
        unrealized_pnl=Decimal("125.75"),
    )
    defaults.update(overrides)
    return ExecutionPosition(**defaults)


# ── import & superficie pública ─────────────────────────────────────────────

class TestImport:
    def test_execution_position_importable_from_package(self):
        assert hasattr(execution_gateway, "ExecutionPosition")
        assert execution_gateway.ExecutionPosition is ExecutionPosition

    def test_execution_position_in_all(self):
        assert "ExecutionPosition" in execution_gateway.__all__

    def test_positions_snapshot_importable_from_package(self):
        assert hasattr(execution_gateway, "PositionsSnapshot")
        assert execution_gateway.PositionsSnapshot is PositionsSnapshot

    def test_positions_snapshot_in_all(self):
        assert "PositionsSnapshot" in execution_gateway.__all__


# ── ExecutionPosition: inmutabilidad y tipos ────────────────────────────────

class TestExecutionPositionContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExecutionPosition)
        assert ExecutionPosition.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExecutionPosition)]
        assert names == ["symbol", "side", "quantity", "entry_price", "leverage", "unrealized_pnl"]

    def test_cannot_reassign_field(self):
        position = _position()
        with pytest.raises(Exception):
            position.symbol = "ETHUSDT"

    def test_no_bybit_types_in_public_attributes(self):
        position = _position()
        public = {k for k in vars(position) if not k.startswith("_")}
        forbidden = {"ret_code", "ret_msg", "result", "positionIdx", "category"}
        assert public.isdisjoint(forbidden)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _position(ret_code=0)

    def test_symbol_must_be_str(self):
        with pytest.raises(TypeError, match="symbol must be str"):
            _position(symbol=123)

    def test_symbol_must_not_be_empty(self):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            _position(symbol="")

    def test_symbol_must_not_be_whitespace(self):
        with pytest.raises(ValueError, match="symbol must not be empty"):
            _position(symbol="   ")

    def test_side_must_be_str(self):
        with pytest.raises(TypeError, match="side must be str"):
            _position(side=1)

    def test_side_accepts_buy(self):
        assert _position(side="buy").side == "buy"

    def test_side_accepts_sell(self):
        assert _position(side="sell").side == "sell"

    def test_side_rejects_capitalized_bybit_vocabulary(self):
        with pytest.raises(ValueError, match="side must be 'buy' or 'sell'"):
            _position(side="Buy")

    def test_side_rejects_unknown_value(self):
        with pytest.raises(ValueError, match="side must be 'buy' or 'sell'"):
            _position(side="long")

    def test_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _position(quantity=0.5)

    def test_quantity_rejects_int(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _position(quantity=1)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity must be > 0"):
            _position(quantity=Decimal("0"))

    def test_quantity_rejects_negative(self):
        with pytest.raises(ValueError, match="quantity must be > 0"):
            _position(quantity=Decimal("-1"))

    def test_quantity_rejects_nan(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _position(quantity=Decimal("nan"))

    def test_quantity_rejects_infinity(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _position(quantity=Decimal("inf"))

    def test_quantity_preserves_exact_decimal(self):
        position = _position(quantity=Decimal("0.00000001"))
        assert position.quantity == Decimal("0.00000001")

    def test_entry_price_must_be_decimal(self):
        with pytest.raises(TypeError, match="entry_price must be Decimal"):
            _position(entry_price=60000.5)

    def test_entry_price_must_be_positive(self):
        with pytest.raises(ValueError, match="entry_price must be > 0"):
            _position(entry_price=Decimal("0"))

    def test_entry_price_rejects_nan(self):
        with pytest.raises(ValueError, match="entry_price must be finite"):
            _position(entry_price=Decimal("nan"))

    def test_entry_price_preserves_many_decimals(self):
        position = _position(entry_price=Decimal("60123.123456789"))
        assert position.entry_price == Decimal("60123.123456789")

    def test_leverage_must_be_decimal(self):
        with pytest.raises(TypeError, match="leverage must be Decimal"):
            _position(leverage=10)

    def test_leverage_must_be_positive(self):
        with pytest.raises(ValueError, match="leverage must be > 0"):
            _position(leverage=Decimal("0"))

    def test_leverage_rejects_infinity(self):
        with pytest.raises(ValueError, match="leverage must be finite"):
            _position(leverage=Decimal("inf"))

    def test_unrealized_pnl_must_be_decimal(self):
        with pytest.raises(TypeError, match="unrealized_pnl must be Decimal"):
            _position(unrealized_pnl=1.0)

    def test_unrealized_pnl_allows_negative(self):
        position = _position(unrealized_pnl=Decimal("-500.25"))
        assert position.unrealized_pnl == Decimal("-500.25")

    def test_unrealized_pnl_allows_zero(self):
        position = _position(unrealized_pnl=Decimal("0"))
        assert position.unrealized_pnl == Decimal("0")

    def test_unrealized_pnl_rejects_nan(self):
        with pytest.raises(ValueError, match="unrealized_pnl must be finite"):
            _position(unrealized_pnl=Decimal("nan"))

    def test_repr_does_not_crash_and_shows_fields(self):
        position = _position()
        text = repr(position)
        assert "BTCUSDT" in text
        assert "buy" in text

    def test_equality_by_value(self):
        assert _position() == _position()

    def test_inequality_on_different_symbol(self):
        assert _position(symbol="BTCUSDT") != _position(symbol="ETHUSDT")


class TestExecutionPositionOptionalAccessoryFields:
    """IMPORTANT-2 (auditoría Hito 3.70): leverage y unrealized_pnl son
    accesorios -- Bybit puede devolverlos vacíos en respuestas válidas
    (p.ej. cuentas Unified en portfolio margin). Deben aceptar None sin
    dejar de validar cuando sí vienen presentes."""

    def test_leverage_none_is_valid(self):
        position = _position(leverage=None)
        assert position.leverage is None

    def test_unrealized_pnl_none_is_valid(self):
        position = _position(unrealized_pnl=None)
        assert position.unrealized_pnl is None

    def test_leverage_field_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionPosition) if f.name == "leverage")
        assert field.default is None

    def test_unrealized_pnl_field_defaults_to_none(self):
        field = next(f for f in dataclasses.fields(ExecutionPosition) if f.name == "unrealized_pnl")
        assert field.default is None

    def test_position_constructible_without_accessory_fields(self):
        position = ExecutionPosition(
            symbol="BTCUSDT", side="buy", quantity=Decimal("1"), entry_price=Decimal("100"),
        )
        assert position.leverage is None
        assert position.unrealized_pnl is None

    def test_leverage_still_validated_when_present(self):
        with pytest.raises(TypeError, match="leverage must be Decimal or None"):
            _position(leverage=10)

    def test_leverage_still_rejects_non_positive_when_present(self):
        with pytest.raises(ValueError, match="leverage must be > 0"):
            _position(leverage=Decimal("0"))

    def test_unrealized_pnl_still_validated_when_present(self):
        with pytest.raises(TypeError, match="unrealized_pnl must be Decimal or None"):
            _position(unrealized_pnl=1.0)

    def test_symbol_side_quantity_entry_price_remain_mandatory(self):
        with pytest.raises(TypeError):
            ExecutionPosition(side="buy", quantity=Decimal("1"), entry_price=Decimal("100"))

    def test_entry_price_still_must_be_positive(self):
        with pytest.raises(ValueError, match="entry_price must be > 0"):
            _position(entry_price=Decimal("0"))


# ── PositionsSnapshot ────────────────────────────────────────────────────

class TestPositionsSnapshotContract:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(PositionsSnapshot)
        assert PositionsSnapshot.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(PositionsSnapshot)]
        assert names == ["positions", "server_time_ms"]

    def test_empty_snapshot_is_valid(self):
        snapshot = PositionsSnapshot(positions=(), server_time_ms=1_700_000_000_000)
        assert snapshot.positions == ()

    def test_positions_must_be_tuple(self):
        with pytest.raises(TypeError, match="positions must be tuple"):
            PositionsSnapshot(positions=[_position()], server_time_ms=1)

    def test_positions_items_must_be_execution_position(self):
        with pytest.raises(TypeError, match="ExecutionPosition"):
            PositionsSnapshot(positions=({"symbol": "BTCUSDT"},), server_time_ms=1)

    def test_positions_preserved_in_order(self):
        p1 = _position(symbol="BTCUSDT")
        p2 = _position(symbol="ETHUSDT")
        snapshot = PositionsSnapshot(positions=(p1, p2), server_time_ms=1)
        assert snapshot.positions == (p1, p2)

    def test_no_duplication_no_loss(self):
        items = tuple(_position(symbol=f"SYM{i}USDT") for i in range(5))
        snapshot = PositionsSnapshot(positions=items, server_time_ms=1)
        assert len(snapshot.positions) == 5
        assert snapshot.positions == items

    def test_server_time_ms_must_be_int(self):
        with pytest.raises(TypeError, match="server_time_ms must be int"):
            PositionsSnapshot(positions=(), server_time_ms=1.5)

    def test_server_time_ms_rejects_bool(self):
        with pytest.raises(TypeError, match="server_time_ms must be int"):
            PositionsSnapshot(positions=(), server_time_ms=True)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time_ms must be >= 0"):
            PositionsSnapshot(positions=(), server_time_ms=-1)

    def test_cannot_reassign_positions(self):
        snapshot = PositionsSnapshot(positions=(), server_time_ms=1)
        with pytest.raises(Exception):
            snapshot.positions = (_position(),)

    def test_no_bybit_types_in_public_attributes(self):
        snapshot = PositionsSnapshot(positions=(), server_time_ms=1)
        public = {k for k in vars(snapshot) if not k.startswith("_")}
        assert public == {"positions", "server_time_ms"}
