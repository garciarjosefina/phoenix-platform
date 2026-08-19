import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.expected_execution_state_contracts import (
    ExpectedExecutionScope,
    ExpectedPosition,
    ExpectedOpenOrder,
    ExpectedExecutionState,
)


def _scope(**overrides):
    defaults = dict(symbols=("BTCUSDT",))
    defaults.update(overrides)
    return ExpectedExecutionScope(**defaults)


def _position(**overrides):
    defaults = dict(symbol="BTCUSDT", side="buy", quantity=Decimal("0.03"))
    defaults.update(overrides)
    return ExpectedPosition(**defaults)


def _order(**overrides):
    defaults = dict(
        order_id="phoenix-order-1",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity=Decimal("0.5"),
        price=Decimal("60000"),
        reduce_only=False,
    )
    defaults.update(overrides)
    return ExpectedOpenOrder(**defaults)


def _state(**overrides):
    defaults = dict(scope=_scope(), positions=(), open_orders=())
    defaults.update(overrides)
    return ExpectedExecutionState(**defaults)


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

class TestImport:
    def test_scope_importable_from_package(self):
        assert hasattr(execution_gateway, "ExpectedExecutionScope")
        assert execution_gateway.ExpectedExecutionScope is ExpectedExecutionScope

    def test_scope_in_all(self):
        assert "ExpectedExecutionScope" in execution_gateway.__all__

    def test_position_importable_from_package(self):
        assert hasattr(execution_gateway, "ExpectedPosition")
        assert execution_gateway.ExpectedPosition is ExpectedPosition

    def test_position_in_all(self):
        assert "ExpectedPosition" in execution_gateway.__all__

    def test_open_order_importable_from_package(self):
        assert hasattr(execution_gateway, "ExpectedOpenOrder")
        assert execution_gateway.ExpectedOpenOrder is ExpectedOpenOrder

    def test_open_order_in_all(self):
        assert "ExpectedOpenOrder" in execution_gateway.__all__

    def test_state_importable_from_package(self):
        assert hasattr(execution_gateway, "ExpectedExecutionState")
        assert execution_gateway.ExpectedExecutionState is ExpectedExecutionState

    def test_state_in_all(self):
        assert "ExpectedExecutionState" in execution_gateway.__all__


# ---------------------------------------------------------------------------
# ExpectedExecutionScope
# ---------------------------------------------------------------------------

class TestExpectedExecutionScope:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExpectedExecutionScope)
        assert ExpectedExecutionScope.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExpectedExecutionScope)]
        assert names == ["symbols"]

    def test_cannot_reassign_field(self):
        scope = _scope()
        with pytest.raises(dataclasses.FrozenInstanceError):
            scope.symbols = ("ETHUSDT",)

    def test_rejects_extra_field(self):
        with pytest.raises(TypeError):
            _scope(foo=1)

    def test_single_symbol_valid(self):
        scope = _scope(symbols=("BTCUSDT",))
        assert scope.symbols == ("BTCUSDT",)

    def test_multiple_symbols_valid(self):
        scope = _scope(symbols=("BTCUSDT", "ETHUSDT", "SOLUSDT"))
        assert scope.symbols == ("BTCUSDT", "ETHUSDT", "SOLUSDT")

    def test_empty_scope_valid(self):
        # Mismo patrón que el resto del read-side: una colección vacía es
        # un resultado legítimo, no un error -- aquí significa que Phoenix
        # no reclama autoridad sobre ningún símbolo todavía.
        scope = _scope(symbols=())
        assert scope.symbols == ()

    def test_duplicate_symbol_rejected(self):
        with pytest.raises(ValueError, match="duplicate symbol"):
            _scope(symbols=("BTCUSDT", "ETHUSDT", "BTCUSDT"))

    def test_empty_string_symbol_rejected(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            _scope(symbols=("BTCUSDT", ""))

    def test_whitespace_only_symbol_rejected(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            _scope(symbols=("   ",))

    def test_non_string_symbol_rejected(self):
        with pytest.raises(TypeError, match="symbols must contain only str"):
            _scope(symbols=(123,))

    def test_symbols_must_be_tuple_not_list(self):
        with pytest.raises(TypeError, match="symbols must be tuple"):
            _scope(symbols=["BTCUSDT"])

    def test_order_preserved(self):
        scope = _scope(symbols=("ETHUSDT", "BTCUSDT"))
        assert scope.symbols == ("ETHUSDT", "BTCUSDT")

    def test_equality_by_value(self):
        assert _scope(symbols=("BTCUSDT",)) == _scope(symbols=("BTCUSDT",))

    def test_repr_does_not_crash(self):
        assert "BTCUSDT" in repr(_scope())


# ---------------------------------------------------------------------------
# ExpectedPosition
# ---------------------------------------------------------------------------

class TestExpectedPosition:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExpectedPosition)
        assert ExpectedPosition.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExpectedPosition)]
        assert names == ["symbol", "side", "quantity"]

    def test_cannot_reassign_field(self):
        position = _position()
        with pytest.raises(dataclasses.FrozenInstanceError):
            position.quantity = Decimal("1")

    def test_buy_valid(self):
        position = _position(side="buy")
        assert position.side == "buy"

    def test_sell_valid(self):
        position = _position(side="sell")
        assert position.side == "sell"

    def test_unknown_side_rejected(self):
        with pytest.raises(ValueError, match="side must be"):
            _position(side="long")

    def test_capitalized_side_rejected(self):
        with pytest.raises(ValueError, match="side must be"):
            _position(side="Buy")

    def test_empty_symbol_rejected(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            _position(symbol="")

    def test_whitespace_symbol_rejected(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            _position(symbol="   ")

    def test_non_string_symbol_rejected(self):
        with pytest.raises(TypeError, match="symbol must be str"):
            _position(symbol=123)

    def test_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _position(quantity=0.03)

    def test_quantity_int_rejected(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _position(quantity=1)

    def test_quantity_str_rejected(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _position(quantity="0.03")

    def test_quantity_positive_valid(self):
        position = _position(quantity=Decimal("0.001"))
        assert position.quantity == Decimal("0.001")

    def test_quantity_zero_rejected(self):
        with pytest.raises(ValueError, match=r"quantity must be > 0"):
            _position(quantity=Decimal("0"))

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValueError, match=r"quantity must be > 0"):
            _position(quantity=Decimal("-1"))

    def test_quantity_nan_rejected(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _position(quantity=Decimal("NaN"))

    def test_quantity_positive_infinity_rejected(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _position(quantity=Decimal("Infinity"))

    def test_quantity_negative_infinity_rejected(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _position(quantity=Decimal("-Infinity"))

    def test_no_entry_price_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedPosition)}
        assert "entry_price" not in names

    def test_no_leverage_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedPosition)}
        assert "leverage" not in names

    def test_no_unrealized_pnl_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedPosition)}
        assert "unrealized_pnl" not in names

    def test_no_bot_id_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedPosition)}
        assert "bot_id" not in names

    def test_no_position_idx_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedPosition)}
        assert "positionIdx" not in names and "position_idx" not in names

    def test_equality_by_value(self):
        assert _position() == _position()

    def test_buy_and_sell_are_distinct_values(self):
        assert _position(side="buy") != _position(side="sell")


# ---------------------------------------------------------------------------
# ExpectedOpenOrder
# ---------------------------------------------------------------------------

class TestExpectedOpenOrder:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExpectedOpenOrder)
        assert ExpectedOpenOrder.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExpectedOpenOrder)]
        assert names == [
            "order_id", "symbol", "side", "order_type", "quantity", "price", "reduce_only",
        ]

    def test_cannot_reassign_field(self):
        order = _order()
        with pytest.raises(dataclasses.FrozenInstanceError):
            order.quantity = Decimal("1")

    def test_valid_limit_order(self):
        order = _order(order_type="limit", price=Decimal("60000"))
        assert order.order_type == "limit"
        assert order.price == Decimal("60000")

    def test_valid_market_order_with_none_price(self):
        order = _order(order_type="market", price=None)
        assert order.price is None

    def test_order_id_empty_rejected(self):
        with pytest.raises(ValueError, match="order_id must not be empty"):
            _order(order_id="")

    def test_order_id_whitespace_rejected(self):
        with pytest.raises(ValueError, match="order_id must not be empty"):
            _order(order_id="   ")

    def test_order_id_non_string_rejected(self):
        with pytest.raises(TypeError, match="order_id must be str"):
            _order(order_id=123)

    def test_order_id_is_phoenix_identity_not_exchange(self):
        # No existe ningun campo exchange_order_id -- la identidad es
        # exclusivamente Phoenix-side.
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "exchange_order_id" not in names

    def test_symbol_empty_rejected(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            _order(symbol="")

    def test_side_buy_valid(self):
        assert _order(side="buy").side == "buy"

    def test_side_sell_valid(self):
        assert _order(side="sell").side == "sell"

    def test_side_invalid_rejected(self):
        with pytest.raises(ValueError, match="side must be"):
            _order(side="long")

    def test_order_type_market_valid(self):
        assert _order(order_type="market", price=None).order_type == "market"

    def test_order_type_limit_valid(self):
        assert _order(order_type="limit").order_type == "limit"

    def test_order_type_invalid_rejected(self):
        with pytest.raises(ValueError, match="order_type must be"):
            _order(order_type="stop")

    def test_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="quantity must be Decimal"):
            _order(quantity=0.5)

    def test_quantity_zero_rejected(self):
        with pytest.raises(ValueError, match=r"quantity must be > 0"):
            _order(quantity=Decimal("0"))

    def test_quantity_negative_rejected(self):
        with pytest.raises(ValueError, match=r"quantity must be > 0"):
            _order(quantity=Decimal("-1"))

    def test_quantity_nan_rejected(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _order(quantity=Decimal("NaN"))

    def test_quantity_infinity_rejected(self):
        with pytest.raises(ValueError, match="quantity must be finite"):
            _order(quantity=Decimal("Infinity"))

    def test_price_none_valid(self):
        order = _order(order_type="market", price=None)
        assert order.price is None

    def test_price_positive_decimal_valid(self):
        order = _order(price=Decimal("100.5"))
        assert order.price == Decimal("100.5")

    def test_price_must_be_decimal_when_present(self):
        with pytest.raises(TypeError, match="price must be Decimal or None"):
            _order(price=100.5)

    def test_price_zero_rejected(self):
        with pytest.raises(ValueError, match=r"price must be > 0"):
            _order(price=Decimal("0"))

    def test_price_negative_rejected(self):
        with pytest.raises(ValueError, match=r"price must be > 0"):
            _order(price=Decimal("-1"))

    def test_price_nan_rejected(self):
        with pytest.raises(ValueError, match="price must be finite"):
            _order(price=Decimal("NaN"))

    def test_price_infinity_rejected(self):
        with pytest.raises(ValueError, match="price must be finite"):
            _order(price=Decimal("Infinity"))

    def test_price_not_coupled_to_order_type(self):
        # Semantica ya aceptada en ExecutionOpenOrder (Hito 3.71):
        # price no se acopla a order_type a nivel de este contrato.
        # Un "limit" con price=None construye sin error aqui -- la
        # decision de si eso es una expectativa valida le corresponde a
        # un consumidor futuro, no a este contrato observacional.
        order = _order(order_type="limit", price=None)
        assert order.price is None

    def test_reduce_only_true_valid(self):
        assert _order(reduce_only=True).reduce_only is True

    def test_reduce_only_false_valid(self):
        assert _order(reduce_only=False).reduce_only is False

    def test_reduce_only_must_be_strict_bool(self):
        with pytest.raises(TypeError, match="reduce_only must be bool"):
            _order(reduce_only="true")

    def test_reduce_only_int_rejected(self):
        with pytest.raises(TypeError, match="reduce_only must be bool"):
            _order(reduce_only=1)

    def test_no_exchange_order_id_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "exchange_order_id" not in names

    def test_no_filled_quantity_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "filled_quantity" not in names

    def test_no_status_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "status" not in names

    def test_no_server_time_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "server_time_ms" not in names and "server_time" not in names

    def test_no_bot_id_field(self):
        names = {f.name for f in dataclasses.fields(ExpectedOpenOrder)}
        assert "bot_id" not in names

    def test_equality_by_value(self):
        assert _order() == _order()

    def test_two_orders_distinct_by_order_id(self):
        assert _order(order_id="a") != _order(order_id="b")


# ---------------------------------------------------------------------------
# ExpectedExecutionState
# ---------------------------------------------------------------------------

class TestExpectedExecutionState:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ExpectedExecutionState)
        assert ExpectedExecutionState.__dataclass_params__.frozen is True

    def test_field_names_exact(self):
        names = [f.name for f in dataclasses.fields(ExpectedExecutionState)]
        assert names == ["scope", "positions", "open_orders"]

    def test_cannot_reassign_field(self):
        state = _state()
        with pytest.raises(dataclasses.FrozenInstanceError):
            state.positions = ()

    def test_scope_must_be_expected_execution_scope(self):
        with pytest.raises(TypeError, match="scope must be ExpectedExecutionScope"):
            _state(scope=object())

    def test_positions_must_be_tuple(self):
        with pytest.raises(TypeError, match="positions must be tuple"):
            _state(positions=[_position()])

    def test_open_orders_must_be_tuple(self):
        with pytest.raises(TypeError, match="open_orders must be tuple"):
            _state(open_orders=[_order()])

    def test_positions_must_contain_only_expected_position(self):
        with pytest.raises(TypeError, match="positions must contain only ExpectedPosition"):
            _state(positions=(object(),))

    def test_open_orders_must_contain_only_expected_open_order(self):
        with pytest.raises(TypeError, match="open_orders must contain only ExpectedOpenOrder"):
            _state(open_orders=(object(),))

    # ── empty vs scoped-flat ─────────────────────────────────────────

    def test_empty_positions_and_open_orders_valid_within_nonempty_scope(self):
        # scope=(BTCUSDT,) + positions=() + open_orders=() significa:
        # Phoenix afirma que NO deberia existir posicion ni orden para
        # BTCUSDT. Es un estado valido y con significado propio.
        state = _state(scope=_scope(symbols=("BTCUSDT",)), positions=(), open_orders=())
        assert state.positions == ()
        assert state.open_orders == ()

    def test_fully_empty_scope_valid(self):
        # Mismo patron aceptado en todo el read-side: coleccion vacia
        # es un resultado legitimo, no un error.
        state = _state(scope=_scope(symbols=()), positions=(), open_orders=())
        assert state.scope.symbols == ()

    # ── containment ──────────────────────────────────────────────────

    def test_position_within_scope_valid(self):
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            positions=(_position(symbol="BTCUSDT"),),
        )
        assert len(state.positions) == 1

    def test_open_order_within_scope_valid(self):
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            open_orders=(_order(symbol="BTCUSDT"),),
        )
        assert len(state.open_orders) == 1

    def test_position_outside_scope_rejected(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                positions=(_position(symbol="ETHUSDT"),),
            )

    def test_open_order_outside_scope_rejected(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                open_orders=(_order(symbol="ETHUSDT"),),
            )

    def test_position_rejected_against_fully_empty_scope(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(scope=_scope(symbols=()), positions=(_position(symbol="BTCUSDT"),))

    # ── duplicate identities ─────────────────────────────────────────

    def test_duplicate_position_identity_rejected(self):
        with pytest.raises(ValueError, match="duplicate position identity"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                positions=(
                    _position(symbol="BTCUSDT", side="buy", quantity=Decimal("1")),
                    _position(symbol="BTCUSDT", side="buy", quantity=Decimal("2")),
                ),
            )

    def test_buy_and_sell_same_symbol_coexist(self):
        # Hedge mode observacional: dos piernas del mismo symbol con
        # side opuesto no son la misma identidad.
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            positions=(
                _position(symbol="BTCUSDT", side="buy", quantity=Decimal("1")),
                _position(symbol="BTCUSDT", side="sell", quantity=Decimal("2")),
            ),
        )
        assert len(state.positions) == 2

    def test_duplicate_order_id_rejected(self):
        with pytest.raises(ValueError, match="duplicate order_id"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                open_orders=(
                    _order(order_id="dup", symbol="BTCUSDT", side="buy"),
                    _order(order_id="dup", symbol="BTCUSDT", side="sell"),
                ),
            )

    def test_economically_identical_orders_distinct_ids_survive(self):
        # Dos ordenes con exactamente los mismos atributos economicos
        # pero order_id distinto NO son duplicados -- la identidad es
        # order_id, nunca los atributos economicos.
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            open_orders=(
                _order(order_id="a", symbol="BTCUSDT", side="buy", quantity=Decimal("1"),
                       price=Decimal("100")),
                _order(order_id="b", symbol="BTCUSDT", side="buy", quantity=Decimal("1"),
                       price=Decimal("100")),
            ),
        )
        assert len(state.open_orders) == 2

    def test_multiple_orders_same_symbol_different_ids_survive(self):
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            open_orders=(
                _order(order_id="a", symbol="BTCUSDT"),
                _order(order_id="b", symbol="BTCUSDT"),
                _order(order_id="c", symbol="BTCUSDT"),
            ),
        )
        assert len(state.open_orders) == 3

    def test_order_preservation(self):
        p1 = _position(symbol="BTCUSDT", side="buy")
        p2 = _position(symbol="BTCUSDT", side="sell")
        state = _state(scope=_scope(symbols=("BTCUSDT",)), positions=(p1, p2))
        assert state.positions == (p1, p2)

    def test_multi_symbol_scope_with_mixed_entities(self):
        state = _state(
            scope=_scope(symbols=("BTCUSDT", "ETHUSDT")),
            positions=(_position(symbol="ETHUSDT", side="buy"),),
            open_orders=(_order(symbol="BTCUSDT"),),
        )
        assert len(state.positions) == 1
        assert len(state.open_orders) == 1

    def test_equality_by_value(self):
        assert _state() == _state()

    def test_repr_does_not_crash(self):
        repr(_state(scope=_scope(symbols=("BTCUSDT",))))


# ---------------------------------------------------------------------------
# Identidad exacta de strings -- sin normalización silenciosa.
#
# Hallazgo IMPORTANTE-1 de la auditoría adversarial independiente del
# Hito 3.76: producción HOY es correcta (no hace strip/upper/lower en
# ningún campo), pero nada en la suite lo aseveraba conductualmente --
# cuatro mutantes que introducían normalización silenciosa (símbolo,
# order_id, comparación de duplicados) sobrevivían. Estos tests fijan
# la semántica actual: identidad de string EXACTA en todo el contrato,
# consistente con que el read-side observado (bybit_positions_response_
# interpreter.py / bybit_open_orders_response_interpreter.py) tampoco
# normaliza -- ambos lados del futuro Reconciliation Engine deben
# seguir siendo simétricos en este eje.
# ---------------------------------------------------------------------------

class TestExactStringIdentityNoNormalization:
    # ── scope: símbolos con distinto casing/espacios son valores distintos ──

    def test_scope_different_case_symbols_are_distinct_and_both_valid(self):
        # Mata M21 (symbol.strip().upper() en scope) y M28 (duplicate
        # detection case-insensitive): si cualquiera de las dos
        # mutaciones estuviera aplicada, esto lanzaría "duplicate
        # symbol" en vez de construir con 2 elementos.
        scope = _scope(symbols=("BTCUSDT", "btcusdt"))
        assert scope.symbols == ("BTCUSDT", "btcusdt")
        assert len(scope.symbols) == 2

    def test_scope_whitespace_padded_symbol_preserved_exactly(self):
        scope = _scope(symbols=(" BTCUSDT ",))
        assert scope.symbols == (" BTCUSDT ",)

    def test_scope_trailing_space_and_bare_symbol_are_distinct(self):
        scope = _scope(symbols=("BTCUSDT", "BTCUSDT "))
        assert scope.symbols == ("BTCUSDT", "BTCUSDT ")
        assert len(scope.symbols) == 2

    def test_scope_duplicate_detection_is_case_sensitive(self):
        # Control positivo: el MISMO string sí sigue siendo rechazado --
        # esto no es una relajación general de la deduplicación.
        with pytest.raises(ValueError, match="duplicate symbol"):
            _scope(symbols=("BTCUSDT", "BTCUSDT"))

    # ── ExpectedPosition.symbol: sin upper/strip ────────────────────────

    def test_position_lowercase_symbol_preserved(self):
        # Mata M31 (ExpectedPosition.symbol = symbol.upper()).
        position = _position(symbol="btcusdt")
        assert position.symbol == "btcusdt"

    def test_position_whitespace_padded_symbol_preserved(self):
        position = _position(symbol=" BTCUSDT ")
        assert position.symbol == " BTCUSDT "

    # ── ExpectedOpenOrder.symbol: sin upper/strip ───────────────────────

    def test_order_lowercase_symbol_preserved(self):
        order = _order(symbol="btcusdt")
        assert order.symbol == "btcusdt"

    def test_order_whitespace_padded_symbol_preserved(self):
        # Mata M32 (ExpectedOpenOrder.symbol = symbol.strip()).
        order = _order(symbol=" BTCUSDT ")
        assert order.symbol == " BTCUSDT "

    # ── order_id: identidad exacta ──────────────────────────────────────

    def test_order_id_different_case_are_distinct_values(self):
        order_upper = _order(order_id="ORDER-1")
        order_lower = _order(order_id="order-1")
        assert order_upper.order_id == "ORDER-1"
        assert order_lower.order_id == "order-1"
        assert order_upper.order_id != order_lower.order_id

    def test_order_id_whitespace_padded_preserved_exactly(self):
        # Mata M20 (order_id = order_id.strip()). Distinto de
        # order_id="   " (whitespace-only), que sigue rechazado --
        # ver test_order_id_whitespace_only_still_rejected.
        order = _order(order_id=" ORDER-1 ")
        assert order.order_id == " ORDER-1 "

    def test_order_id_whitespace_only_still_rejected(self):
        # Control positivo: no se relaja el rechazo de whitespace-only,
        # sólo se protege que un id CON contenido no se recorte.
        with pytest.raises(ValueError, match="order_id must not be empty"):
            _order(order_id="   ")

    def test_two_orders_case_variant_order_ids_both_survive(self):
        # Mata M34 (duplicate order_id detection case-insensitive).
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            open_orders=(_order(order_id="ORDER-1"), _order(order_id="order-1")),
        )
        assert len(state.open_orders) == 2

    def test_two_orders_whitespace_variant_order_ids_both_survive(self):
        # Mata M35 (duplicate order_id detection strip-aware).
        state = _state(
            scope=_scope(symbols=("BTCUSDT",)),
            open_orders=(_order(order_id="ORDER-1"), _order(order_id=" ORDER-1 ")),
        )
        assert len(state.open_orders) == 2

    # ── containment: comparación exacta, no case/whitespace-insensitive ──

    def test_position_different_case_symbol_rejected_as_out_of_scope(self):
        # Mata M33 (scope membership comparison case-insensitive): si
        # la comparación fuera case-insensitive, "btcusdt" pasaría
        # contra scope=("BTCUSDT",).
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                positions=(_position(symbol="btcusdt"),),
            )

    def test_position_whitespace_padded_symbol_rejected_as_out_of_scope(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                positions=(_position(symbol=" BTCUSDT "),),
            )

    def test_order_different_case_symbol_rejected_as_out_of_scope(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                open_orders=(_order(symbol="btcusdt"),),
            )

    def test_order_whitespace_padded_symbol_rejected_as_out_of_scope(self):
        with pytest.raises(ValueError, match="not in scope"):
            _state(
                scope=_scope(symbols=("BTCUSDT",)),
                open_orders=(_order(symbol=" BTCUSDT "),),
            )

    def test_position_exact_case_match_against_lowercase_scope_valid(self):
        # Control positivo: coincidencia EXACTA (incluido casing) sigue
        # funcionando -- containment no está simplemente roto.
        state = _state(
            scope=_scope(symbols=("btcusdt",)),
            positions=(_position(symbol="btcusdt"),),
        )
        assert len(state.positions) == 1

    # ── MARKET + price>0: valor preservado, sin conversión silenciosa ───

    def test_market_order_with_positive_price_preserves_value_exactly(self):
        # Mata M19 (MARKET + price>0 convertido silenciosamente a None).
        # Nota: esto fija el comportamiento ACTUAL del contrato -- no
        # decide si esta semántica es la ideal para un futuro
        # Reconciliation Engine (ver MENOR-1, docs/decisions.md ADR-004).
        order = _order(order_type="market", price=Decimal("50000"))
        assert order.order_type == "market"
        assert order.price == Decimal("50000")


# ---------------------------------------------------------------------------
# Pureza de dominio (AST)
# ---------------------------------------------------------------------------

class TestPurityByAst:
    _FORBIDDEN_SUBSTRINGS = ("bybit", "urllib", "http", "requests", "socket", "railway", "os")

    def _module_imports(self, module) -> list[str]:
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(module))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def test_module_imports_only_stdlib(self):
        import execution_gateway.expected_execution_state_contracts as module
        imports = self._module_imports(module)
        assert set(imports) == {"dataclasses", "decimal"}

    def test_module_has_no_forbidden_imports(self):
        import execution_gateway.expected_execution_state_contracts as module
        imports = self._module_imports(module)
        violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
        assert violations == []

    def test_module_has_no_reconciliation_vocabulary_as_code(self):
        # Prosa explicativa en docstrings/comentarios puede legitimamente
        # mencionar "Reconciliation Engine" al describir que algo queda
        # deliberadamente fuera de alcance (igual que en otros contratos
        # ya aceptados del repo) -- lo que se prohibe es que esa palabra
        # aparezca como CODIGO real (nombre de clase/funcion/variable),
        # no en la prosa. Se escanea el AST, no el texto crudo.
        import ast
        import inspect
        import execution_gateway.expected_execution_state_contracts as module

        tree = ast.parse(inspect.getsource(module))
        banned = ("reconcile", "Reconcil", "MATCH", "MISSING", "UNEXPECTED", "MISMATCH", "repair")
        identifiers: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                identifiers.append(node.name)
            elif isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.append(node.attr)
        offenders = [i for i in identifiers if any(b in i for b in banned)]
        assert offenders == []

    def test_module_does_not_reference_exchange_state_snapshot(self):
        import inspect
        import execution_gateway.expected_execution_state_contracts as module
        src = inspect.getsource(module)
        assert "ExchangeStateSnapshot" not in src

    def test_module_has_no_side_effects_on_import(self):
        # Reload no debe ejecutar I/O ni levantar excepcion.
        import importlib
        import execution_gateway.expected_execution_state_contracts as module
        importlib.reload(module)
