import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.expected_execution_state_contracts as _expected_execution_state_contracts
from execution_gateway.expected_execution_state_contracts import ExpectedExecutionState
from execution_gateway.positions_contracts import ExecutionPosition, PositionsSnapshot
from execution_gateway.open_orders_contracts import ExecutionOpenOrder, OpenOrdersSnapshot
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot
from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot, ObservationWindow
from execution_gateway.reconciliation_precondition_error import ReconciliationPreconditionError
from execution_gateway.reconciliation_contracts import (
    Divergence,
    MissingExpectedPosition,
    UnexpectedExchangePosition,
    PositionQuantityMismatch,
    MissingExpectedOpenOrder,
    UnexpectedExchangeOpenOrder,
    UnattributedExchangeOpenOrder,
    OrderSymbolMismatch,
    OrderSideMismatch,
    OrderQuantityMismatch,
    OrderTypeMismatch,
    OrderPriceMismatch,
    ReconciliationResult,
)
from execution_gateway.reconciliation_engine import reconcile_execution_state


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _scope(**overrides):
    # Nota de aislamiento de tests: construye vía atributo de módulo
    # "fresco" (no `from ... import ExpectedExecutionScope` capturado una
    # sola vez en la colección) porque
    # test_execution_gateway_expected_execution_state_contracts.py
    # (archivo protegido/ya aceptado en 3.76) tiene un test que hace
    # `importlib.reload()` sobre este módulo -- si esta función usara una
    # referencia de clase capturada antes del reload, el isinstance()
    # dinámico dentro de ExpectedExecutionState.__post_init__ (que sí
    # resuelve sus globals en el momento de la llamada) fallaría para
    # cualquier test que corra después, según el orden alfabético de
    # ejecución de pytest. ExpectedExecutionState en sí NO necesita este
    # tratamiento porque reconciliation_engine.py ya capturó su propia
    # referencia (también "vieja") en el momento de la colección -- ambas
    # quedan consistentes entre sí.
    defaults = dict(symbols=("BTCUSDT",))
    defaults.update(overrides)
    return _expected_execution_state_contracts.ExpectedExecutionScope(**defaults)


def _exp_position(**overrides):
    defaults = dict(symbol="BTCUSDT", side="buy", quantity=Decimal("1"))
    defaults.update(overrides)
    return _expected_execution_state_contracts.ExpectedPosition(**defaults)


def _exp_order(**overrides):
    defaults = dict(
        order_id="PHX-1", symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("1"), price=Decimal("100"), reduce_only=False,
    )
    defaults.update(overrides)
    return _expected_execution_state_contracts.ExpectedOpenOrder(**defaults)


def _exp_state(**overrides):
    defaults = dict(scope=_scope(), positions=(), open_orders=())
    defaults.update(overrides)
    return ExpectedExecutionState(**defaults)


def _obs_position(**overrides):
    defaults = dict(symbol="BTCUSDT", side="buy", quantity=Decimal("1"), entry_price=Decimal("100"))
    defaults.update(overrides)
    return ExecutionPosition(**defaults)


def _obs_order(**overrides):
    defaults = dict(
        exchange_order_id="BYBIT-1", order_id="PHX-1", symbol="BTCUSDT", side="buy",
        order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("0"),
        status="new", reduce_only=False, price=Decimal("100"),
    )
    defaults.update(overrides)
    return ExecutionOpenOrder(**defaults)


def _snapshot(*, positions=(), orders=(), t=1000):
    return ExchangeStateSnapshot(
        positions=PositionsSnapshot(positions=positions, server_time_ms=t),
        open_orders=OpenOrdersSnapshot(orders=orders, server_time_ms=t),
        wallet_balance=WalletBalanceSnapshot(
            total_equity=Decimal("1"), total_wallet_balance=Decimal("1"),
            total_available_balance=Decimal("1"), total_initial_margin=Decimal("0"),
            total_maintenance_margin=Decimal("0"), currency_balances=(), server_time_ms=t,
        ),
        observation_window=ObservationWindow(
            earliest_remote_time_ms=t, latest_remote_time_ms=t, remote_time_span_ms=0,
        ),
    )


def _reconcile(expected=None, observed=None):
    return reconcile_execution_state(
        expected=expected if expected is not None else _exp_state(),
        observed=observed if observed is not None else _snapshot(),
    )


# ---------------------------------------------------------------------------
# Imports
# ---------------------------------------------------------------------------

class TestImport:
    @pytest.mark.parametrize("name", [
        "ReconciliationPreconditionError", "Divergence", "MissingExpectedPosition",
        "UnexpectedExchangePosition", "PositionQuantityMismatch", "MissingExpectedOpenOrder",
        "UnexpectedExchangeOpenOrder", "UnattributedExchangeOpenOrder", "OrderSymbolMismatch",
        "OrderSideMismatch", "OrderQuantityMismatch", "OrderTypeMismatch", "OrderPriceMismatch",
        "ReconciliationResult", "reconcile_execution_state",
    ])
    def test_importable_from_package_and_in_all(self, name):
        assert hasattr(execution_gateway, name)
        assert name in execution_gateway.__all__

    def test_reconcile_execution_state_is_module_function(self):
        assert execution_gateway.reconcile_execution_state is reconcile_execution_state


# ---------------------------------------------------------------------------
# Divergence dataclasses: frozen, validated, equality by value
# ---------------------------------------------------------------------------

class TestDivergenceDataclasses:
    def test_all_divergence_types_are_frozen_dataclasses_and_subclass_divergence(self):
        types_ = [
            MissingExpectedPosition, UnexpectedExchangePosition, PositionQuantityMismatch,
            MissingExpectedOpenOrder, UnexpectedExchangeOpenOrder, UnattributedExchangeOpenOrder,
            OrderSymbolMismatch, OrderSideMismatch, OrderQuantityMismatch, OrderTypeMismatch,
            OrderPriceMismatch,
        ]
        for t in types_:
            assert dataclasses.is_dataclass(t)
            assert t.__dataclass_params__.frozen is True
            assert issubclass(t, Divergence)

    def test_missing_expected_position_fields(self):
        d = MissingExpectedPosition(symbol="BTCUSDT", side="buy", expected_quantity=Decimal("1"))
        assert d.symbol == "BTCUSDT" and d.side == "buy" and d.expected_quantity == Decimal("1")

    def test_missing_expected_position_rejects_bad_side(self):
        with pytest.raises(ValueError, match="side must be"):
            MissingExpectedPosition(symbol="A", side="long", expected_quantity=Decimal("1"))

    def test_position_quantity_mismatch_rejects_non_decimal(self):
        with pytest.raises(TypeError, match="expected_quantity must be Decimal"):
            PositionQuantityMismatch(symbol="A", side="buy", expected_quantity=1, observed_quantity=Decimal("1"))

    def test_order_price_mismatch_allows_none_on_either_side(self):
        d = OrderPriceMismatch(order_id="X", expected_price=None, observed_price=Decimal("1"))
        assert d.expected_price is None and d.observed_price == Decimal("1")

    def test_order_price_mismatch_rejects_nan(self):
        with pytest.raises(ValueError, match="finite"):
            OrderPriceMismatch(order_id="X", expected_price=Decimal("NaN"), observed_price=None)

    def test_unattributed_has_exchange_order_id_not_order_id(self):
        names = {f.name for f in dataclasses.fields(UnattributedExchangeOpenOrder)}
        assert "exchange_order_id" in names
        assert "order_id" not in names

    def test_frozen_instances_immutable(self):
        d = MissingExpectedPosition(symbol="A", side="buy", expected_quantity=Decimal("1"))
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.symbol = "B"

    def test_equality_by_value(self):
        a = OrderSymbolMismatch(order_id="X", expected_symbol="A", observed_symbol="B")
        b = OrderSymbolMismatch(order_id="X", expected_symbol="A", observed_symbol="B")
        assert a == b


# ---------------------------------------------------------------------------
# ReconciliationResult
# ---------------------------------------------------------------------------

class TestReconciliationResult:
    def test_is_frozen_dataclass(self):
        assert dataclasses.is_dataclass(ReconciliationResult)
        assert ReconciliationResult.__dataclass_params__.frozen is True

    def test_empty_divergences_means_in_sync(self):
        r = ReconciliationResult(divergences=(), observation_window=_snapshot().observation_window)
        assert r.is_in_sync is True

    def test_non_empty_divergences_means_not_in_sync(self):
        d = (MissingExpectedPosition(symbol="A", side="buy", expected_quantity=Decimal("1")),)
        r = ReconciliationResult(divergences=d, observation_window=_snapshot().observation_window)
        assert r.is_in_sync is False

    def test_is_in_sync_is_a_property_not_a_field(self):
        names = {f.name for f in dataclasses.fields(ReconciliationResult)}
        assert "is_in_sync" not in names
        assert isinstance(ReconciliationResult.__dict__["is_in_sync"], property)

    def test_divergences_must_be_tuple(self):
        with pytest.raises(TypeError, match="divergences must be tuple"):
            ReconciliationResult(divergences=[], observation_window=_snapshot().observation_window)

    def test_divergences_must_contain_only_divergence_instances(self):
        with pytest.raises(TypeError, match="must contain only Divergence"):
            ReconciliationResult(divergences=(object(),), observation_window=_snapshot().observation_window)

    def test_observation_window_must_be_observation_window(self):
        with pytest.raises(TypeError, match="observation_window must be ObservationWindow"):
            ReconciliationResult(divergences=(), observation_window=object())

    def test_frozen(self):
        r = ReconciliationResult(divergences=(), observation_window=_snapshot().observation_window)
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.divergences = ()


# ---------------------------------------------------------------------------
# Positions -- Sección 21
# ---------------------------------------------------------------------------

class TestPositionsReconciliation:
    def test_expected_equals_observed_no_divergence(self):
        expected = _exp_state(scope=_scope(), positions=(_exp_position(quantity=Decimal("1")),))
        observed = _snapshot(positions=(_obs_position(quantity=Decimal("1")),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_missing_expected_position(self):
        expected = _exp_state(scope=_scope(), positions=(_exp_position(quantity=Decimal("1")),))
        observed = _snapshot()
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], MissingExpectedPosition)
        assert r.divergences[0].expected_quantity == Decimal("1")

    def test_observed_position_unexpected_within_scope(self):
        expected = _exp_state(scope=_scope())
        observed = _snapshot(positions=(_obs_position(quantity=Decimal("2")),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], UnexpectedExchangePosition)
        assert r.divergences[0].observed_quantity == Decimal("2")

    def test_observed_position_outside_scope_ignored(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(positions=(_obs_position(symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_quantity_mismatch(self):
        expected = _exp_state(scope=_scope(), positions=(_exp_position(quantity=Decimal("1")),))
        observed = _snapshot(positions=(_obs_position(quantity=Decimal("2")),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        d = r.divergences[0]
        assert isinstance(d, PositionQuantityMismatch)
        assert d.expected_quantity == Decimal("1") and d.observed_quantity == Decimal("2")

    def test_buy_and_sell_are_independent_identities(self):
        expected = _exp_state(
            scope=_scope(),
            positions=(_exp_position(side="buy", quantity=Decimal("1")),
                       _exp_position(side="sell", quantity=Decimal("2"))),
        )
        observed = _snapshot(positions=(
            _obs_position(side="buy", quantity=Decimal("1")),
            _obs_position(side="sell", quantity=Decimal("2")),
        ))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_matching_includes_side(self):
        # expected BUY 1, observed SELL 1 -- distinta identidad, no matched.
        expected = _exp_state(scope=_scope(), positions=(_exp_position(side="buy", quantity=Decimal("1")),))
        observed = _snapshot(positions=(_obs_position(side="sell", quantity=Decimal("1")),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {MissingExpectedPosition, UnexpectedExchangePosition}

    def test_symbol_exact_identity_no_normalization(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)), positions=(_exp_position(symbol="BTCUSDT"),))
        observed = _snapshot(positions=(_obs_position(symbol="btcusdt"),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        # "BTCUSDT" y "btcusdt" son identidades distintas: expected queda
        # missing, y observed queda fuera de scope (case-sensitive) -> ignorada.
        assert kinds == {MissingExpectedPosition}

    def test_casing_not_normalized_produces_distinct_identities(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT", "btcusdt")),
                               positions=(_exp_position(symbol="BTCUSDT"), _exp_position(symbol="btcusdt")))
        observed = _snapshot(positions=(_obs_position(symbol="BTCUSDT"), _obs_position(symbol="btcusdt")))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_padding_not_normalized(self):
        expected = _exp_state(scope=_scope(symbols=(" BTCUSDT",)), positions=(_exp_position(symbol=" BTCUSDT"),))
        observed = _snapshot(positions=(_obs_position(symbol=" BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_scope_exact_identity(self):
        # scope tiene "BTCUSDT " (con espacio), observed "BTCUSDT" sin espacio -> fuera de scope.
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT ",)))
        observed = _snapshot(positions=(_obs_position(symbol="BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync  # "BTCUSDT" no esta en scope=("BTCUSDT ",)

    def test_empty_scope_empty_expected_observed_out_of_scope_in_sync(self):
        expected = _exp_state(scope=_scope(symbols=()))
        observed = _snapshot(positions=(_obs_position(symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_empty_scope_grants_no_authority_over_observed_positions(self):
        expected = _exp_state(scope=_scope(symbols=()))
        observed = _snapshot(positions=(_obs_position(symbol="BTCUSDT"),))
        r = _reconcile(expected, observed)
        # BTCUSDT no esta en scope=() -> ignorada, no UnexpectedExchangePosition.
        assert r.is_in_sync


# ---------------------------------------------------------------------------
# Órdenes -- Sección 22
# ---------------------------------------------------------------------------

class TestOpenOrdersReconciliation:
    def test_matched_exact_no_divergence(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(),))
        observed = _snapshot(orders=(_obs_order(),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_missing_expected_order(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(),))
        observed = _snapshot()
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], MissingExpectedOpenOrder)

    def test_unexpected_order_within_scope(self):
        expected = _exp_state(scope=_scope())
        observed = _snapshot(orders=(_obs_order(order_id="PHX-999"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], UnexpectedExchangeOpenOrder)
        assert r.divergences[0].order_id == "PHX-999"

    def test_unexpected_order_outside_scope_ignored(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(orders=(_obs_order(order_id="PHX-999", symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_orphan_order_id_none_within_scope(self):
        expected = _exp_state(scope=_scope())
        observed = _snapshot(orders=(_obs_order(order_id=None),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], UnattributedExchangeOpenOrder)

    def test_orphan_outside_scope_ignored(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(orders=(_obs_order(order_id=None, symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_symbol_mismatch(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT", "ETHUSDT")), open_orders=(_exp_order(symbol="BTCUSDT"),))
        observed = _snapshot(orders=(_obs_order(symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        d = r.divergences[0]
        assert isinstance(d, OrderSymbolMismatch)
        assert d.expected_symbol == "BTCUSDT" and d.observed_symbol == "ETHUSDT"

    def test_side_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(side="buy"),))
        observed = _snapshot(orders=(_obs_order(side="sell"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderSideMismatch)

    def test_quantity_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(quantity=Decimal("1")),))
        observed = _snapshot(orders=(_obs_order(quantity=Decimal("2")),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        d = r.divergences[0]
        assert isinstance(d, OrderQuantityMismatch)
        assert d.expected_quantity == Decimal("1") and d.observed_quantity == Decimal("2")

    def test_order_type_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("1")),))
        observed = _snapshot(orders=(_obs_order(order_type="market", price=None),))
        r = _reconcile(expected, observed)
        kinds = [type(d) for d in r.divergences]
        assert OrderTypeMismatch in kinds

    def test_limit_price_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("100")),))
        observed = _snapshot(orders=(_obs_order(order_type="limit", price=Decimal("200")),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        d = r.divergences[0]
        assert isinstance(d, OrderPriceMismatch)
        assert d.expected_price == Decimal("100") and d.observed_price == Decimal("200")

    def test_limit_observed_price_none(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("100")),))
        observed = _snapshot(orders=(_obs_order(order_type="limit", price=None),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderPriceMismatch)

    def test_market_price_ignored_when_observed_price_present(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="market", price=None),))
        observed = _snapshot(orders=(_obs_order(order_type="market", price=Decimal("999")),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_market_expected_price_none_valid(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="market", price=None),))
        observed = _snapshot(orders=(_obs_order(order_type="market", price=None),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_market_expected_price_positive_preserved_but_not_reconciled(self):
        order = _exp_order(order_type="market", price=Decimal("50000"))
        assert order.price == Decimal("50000")
        expected = _exp_state(scope=_scope(), open_orders=(order,))
        observed = _snapshot(orders=(_obs_order(order_type="market", price=None),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync
        assert order.price == Decimal("50000")  # sigue intacto, nunca borrado/normalizado

    def test_multiple_mismatches_produce_multiple_divergences(self):
        expected = _exp_state(
            scope=_scope(symbols=("BTCUSDT", "ETHUSDT")),
            open_orders=(_exp_order(symbol="BTCUSDT", side="buy", quantity=Decimal("1"),
                                     order_type="limit", price=Decimal("1")),),
        )
        observed = _snapshot(orders=(_obs_order(symbol="ETHUSDT", side="sell", quantity=Decimal("2"),
                                                  order_type="limit", price=Decimal("2")),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {OrderSymbolMismatch, OrderSideMismatch, OrderQuantityMismatch, OrderPriceMismatch}

    def test_identity_first_symbol_mismatch_not_ignored_despite_scope(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)), open_orders=(_exp_order(symbol="BTCUSDT"),))
        observed = _snapshot(orders=(_obs_order(symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderSymbolMismatch)

    def test_exchange_order_id_never_used_as_fallback(self):
        # order_id de expected NO coincide con exchange_order_id de observed
        # -- deben tratarse como entidades distintas (missing + unexpected),
        # nunca como matched.
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_id="PHX-1"),))
        observed = _snapshot(orders=(_obs_order(order_id="PHX-2", exchange_order_id="PHX-1"),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {MissingExpectedOpenOrder, UnexpectedExchangeOpenOrder}

    def test_exchange_order_id_of_orphan_never_matches_expected_order_id(self):
        # Una orden huerfana (order_id=None) cuyo exchange_order_id
        # COINCIDE por casualidad con el order_id Phoenix de una orden
        # esperada NO debe matchear -- exchange_order_id nunca participa
        # como fallback de identidad. La expectativa sigue "missing" y la
        # huerfana sigue reportandose por separado (dentro de scope).
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_id="PHX-1"),))
        observed = _snapshot(orders=(
            _obs_order(order_id=None, exchange_order_id="PHX-1"),
        ))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {MissingExpectedOpenOrder, UnattributedExchangeOpenOrder}

    def test_order_id_padding_matches_when_identical_on_both_sides(self):
        # order_id con el MISMO padding en ambos lados debe matchear
        # limpiamente -- protege contra una normalizacion (strip) que
        # rompa la busqueda por clave exacta.
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_id=" PHX-1 "),))
        observed = _snapshot(orders=(_obs_order(order_id=" PHX-1 "),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_scope_lowercase_symbol_does_not_match_uppercase_observed(self):
        # scope declarado en minusculas; symbol observado en mayusculas --
        # deben tratarse como fuera de scope (case-sensitive), protegiendo
        # contra una normalizacion .upper()/.lower() del scope.
        expected = _exp_state(scope=_scope(symbols=("btcusdt",)))
        observed = _snapshot(positions=(_obs_position(symbol="BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_order_id_casing_exact(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_id="PHX-1"),))
        observed = _snapshot(orders=(_obs_order(order_id="phx-1"),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {MissingExpectedOpenOrder, UnexpectedExchangeOpenOrder}

    def test_order_id_padding_exact(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_id="PHX-1"),))
        observed = _snapshot(orders=(_obs_order(order_id=" PHX-1 "),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert kinds == {MissingExpectedOpenOrder, UnexpectedExchangeOpenOrder}

    def test_symbol_casing_exact_on_matched_order(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)), open_orders=(_exp_order(symbol="BTCUSDT"),))
        observed = _snapshot(orders=(_obs_order(symbol="btcusdt"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderSymbolMismatch)

    def test_symbol_padding_exact_on_matched_order(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)), open_orders=(_exp_order(symbol="BTCUSDT"),))
        observed = _snapshot(orders=(_obs_order(symbol=" BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderSymbolMismatch)

    def test_matched_order_not_split_into_missing_and_unexpected(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(price=Decimal("1")),))
        observed = _snapshot(orders=(_obs_order(price=Decimal("2")),))
        r = _reconcile(expected, observed)
        kinds = {type(d) for d in r.divergences}
        assert MissingExpectedOpenOrder not in kinds
        assert UnexpectedExchangeOpenOrder not in kinds

    def test_partial_fill_does_not_compare_remaining_quantity(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(quantity=Decimal("10")),))
        observed = _snapshot(orders=(_obs_order(quantity=Decimal("10"), filled_quantity=Decimal("7")),))
        r = _reconcile(expected, observed)
        # quantity (10) coincide con expected -- filled_quantity nunca se resta.
        assert r.is_in_sync

    def test_scope_lowercase_symbol_does_not_match_uppercase_observed_unattributed(self):
        # Mismo control que en posiciones, pero contra el scope_symbols
        # independiente calculado dentro de _reconcile_open_orders.
        expected = _exp_state(scope=_scope(symbols=("btcusdt",)))
        observed = _snapshot(orders=(_obs_order(order_id=None, symbol="BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_observed_status_alone_never_produces_divergence(self):
        for status in ("new", "partially_filled", "untriggered", "triggered"):
            expected = _exp_state(scope=_scope(), open_orders=(_exp_order(),))
            observed = _snapshot(orders=(_obs_order(status=status),))
            r = _reconcile(expected, observed)
            assert r.is_in_sync, f"status={status} should not affect sync"


# ---------------------------------------------------------------------------
# Price precondition -- Sección 23
# ---------------------------------------------------------------------------

class TestPricePrecondition:
    def test_expected_limit_price_none_fails_closed(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=None),))
        with pytest.raises(ReconciliationPreconditionError):
            _reconcile(expected, _snapshot())

    def test_expected_limit_price_valid_ok(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("1")),))
        r = _reconcile(expected, _snapshot(orders=(_obs_order(order_type="limit", price=Decimal("1")),)))
        assert r.is_in_sync

    def test_expected_market_price_none_valid(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="market", price=None),))
        r = _reconcile(expected, _snapshot(orders=(_obs_order(order_type="market", price=None),)))
        assert r.is_in_sync

    def test_expected_market_price_positive_valid_and_preserved(self):
        order = _exp_order(order_type="market", price=Decimal("50000"))
        expected = _exp_state(scope=_scope(), open_orders=(order,))
        r = _reconcile(expected, _snapshot(orders=(_obs_order(order_type="market", price=None),)))
        assert r.is_in_sync
        assert order.price == Decimal("50000")

    def test_market_with_different_observed_price_no_price_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="market", price=None),))
        observed = _snapshot(orders=(_obs_order(order_type="market", price=Decimal("123")),))
        r = _reconcile(expected, observed)
        assert not any(isinstance(d, OrderPriceMismatch) for d in r.divergences)

    def test_limit_with_different_price_produces_price_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("1")),))
        observed = _snapshot(orders=(_obs_order(order_type="limit", price=Decimal("2")),))
        r = _reconcile(expected, observed)
        assert any(isinstance(d, OrderPriceMismatch) for d in r.divergences)

    def test_limit_observed_price_none_produces_price_mismatch(self):
        expected = _exp_state(scope=_scope(), open_orders=(_exp_order(order_type="limit", price=Decimal("1")),))
        observed = _snapshot(orders=(_obs_order(order_type="limit", price=None),))
        r = _reconcile(expected, observed)
        assert any(isinstance(d, OrderPriceMismatch) for d in r.divergences)

    def test_precondition_checked_before_any_matching(self):
        # Aunque exista tambien una MissingExpectedPosition potencial, la
        # precondicion de price debe abortar ANTES de producir cualquier
        # divergencia -- no debe haber ReconciliationResult parcial.
        expected = _exp_state(
            scope=_scope(),
            positions=(_exp_position(),),
            open_orders=(_exp_order(order_type="limit", price=None),),
        )
        with pytest.raises(ReconciliationPreconditionError):
            _reconcile(expected, _snapshot())


# ---------------------------------------------------------------------------
# Identity-first / scope-second -- Sección 24, casos A-D exactos del prompt
# ---------------------------------------------------------------------------

class TestIdentityFirstScopeSecond:
    def test_caso_a_matched_identity_with_symbol_outside_scope_still_mismatches(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)),
                               open_orders=(_exp_order(order_id="PHX-123", symbol="BTCUSDT"),))
        observed = _snapshot(orders=(_obs_order(order_id="PHX-123", symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        assert isinstance(r.divergences[0], OrderSymbolMismatch)
        assert r.divergences[0].order_id == "PHX-123"

    def test_caso_b_unmatched_order_outside_scope_ignored(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(orders=(_obs_order(order_id="PHX-999", symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_caso_c_orphan_outside_scope_ignored(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(orders=(_obs_order(order_id=None, exchange_order_id="BYBIT-999", symbol="ETHUSDT"),))
        r = _reconcile(expected, observed)
        assert r.is_in_sync

    def test_caso_d_orphan_within_scope_unattributed(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT",)))
        observed = _snapshot(orders=(_obs_order(order_id=None, exchange_order_id="BYBIT-999", symbol="BTCUSDT"),))
        r = _reconcile(expected, observed)
        assert len(r.divergences) == 1
        d = r.divergences[0]
        assert isinstance(d, UnattributedExchangeOpenOrder)
        assert d.exchange_order_id == "BYBIT-999"


# ---------------------------------------------------------------------------
# Determinismo -- Sección 25
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_input_same_result(self):
        expected = _exp_state(scope=_scope(symbols=("BTCUSDT", "ETHUSDT")),
                               positions=(_exp_position(symbol="BTCUSDT"),),
                               open_orders=(_exp_order(symbol="ETHUSDT", order_id="PHX-1"),))
        observed = _snapshot()
        r1 = _reconcile(expected, observed)
        r2 = _reconcile(expected, observed)
        assert r1 == r2
        assert r1.divergences == r2.divergences

    def test_stable_order_of_divergences_across_repeated_calls(self):
        expected = _exp_state(
            scope=_scope(symbols=("A", "B", "C")),
            positions=(_exp_position(symbol="A"), _exp_position(symbol="B"), _exp_position(symbol="C")),
        )
        observed = _snapshot()
        results = [_reconcile(expected, observed).divergences for _ in range(5)]
        assert all(r == results[0] for r in results)

    def test_multiple_mismatches_fixed_field_order(self):
        # expected.order_type sigue siendo "limit" (con price), asi que el
        # motor SI compara price contra lo observado -- produce las 5
        # divergencias en el orden fijo symbol/side/quantity/order_type/price.
        expected = _exp_state(
            scope=_scope(symbols=("BTCUSDT", "ETHUSDT")),
            open_orders=(_exp_order(symbol="BTCUSDT", side="buy", quantity=Decimal("1"),
                                     order_type="limit", price=Decimal("1")),),
        )
        observed = _snapshot(orders=(_obs_order(symbol="ETHUSDT", side="sell", quantity=Decimal("2"),
                                                  order_type="market", price=None),))
        r = _reconcile(expected, observed)
        expected_order = [
            OrderSymbolMismatch, OrderSideMismatch, OrderQuantityMismatch,
            OrderTypeMismatch, OrderPriceMismatch,
        ]
        assert [type(d) for d in r.divergences] == expected_order

    def test_expected_ordering_preserved_in_missing_positions(self):
        expected = _exp_state(
            scope=_scope(symbols=("C", "A", "B")),
            positions=(_exp_position(symbol="C"), _exp_position(symbol="A"), _exp_position(symbol="B")),
        )
        r = _reconcile(expected, _snapshot())
        assert [d.symbol for d in r.divergences] == ["C", "A", "B"]

    def test_observed_unmatched_ordering_preserved(self):
        expected = _exp_state(scope=_scope(symbols=("C", "A", "B")))
        observed = _snapshot(positions=(
            _obs_position(symbol="C"), _obs_position(symbol="A"), _obs_position(symbol="B"),
        ))
        r = _reconcile(expected, observed)
        assert [d.symbol for d in r.divergences] == ["C", "A", "B"]

    def test_no_dependence_on_set_iteration_order(self):
        # Repite con un scope grande -- el resultado (incluido el ORDEN)
        # no debe depender del hash interno de python (dict/set), sino del
        # orden contractual de observed.positions.positions.
        symbols = tuple(f"SYM{i}" for i in range(20))
        expected = _exp_state(scope=_scope(symbols=symbols))
        observed = _snapshot(positions=tuple(_obs_position(symbol=s) for s in symbols))
        results = [_reconcile(expected, observed).divergences for _ in range(3)]
        assert all(r == results[0] for r in results)
        assert [d.symbol for d in results[0]] == list(symbols)
        assert all(isinstance(d, UnexpectedExchangePosition) for d in results[0])


# ---------------------------------------------------------------------------
# Pureza -- Sección 26
# ---------------------------------------------------------------------------

class TestPurity:
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

    def test_reconciliation_contracts_module_imports(self):
        import execution_gateway.reconciliation_contracts as module
        imports = self._module_imports(module)
        assert set(imports) == {
            "dataclasses", "decimal", "execution_gateway.exchange_state_contracts",
        }

    def test_reconciliation_engine_module_imports(self):
        import execution_gateway.reconciliation_engine as module
        imports = self._module_imports(module)
        assert set(imports) == {
            "execution_gateway.exchange_state_contracts",
            "execution_gateway.expected_execution_state_contracts",
            "execution_gateway.reconciliation_contracts",
            "execution_gateway.reconciliation_precondition_error",
        }

    def test_reconciliation_precondition_error_module_imports(self):
        import execution_gateway.reconciliation_precondition_error as module
        imports = self._module_imports(module)
        assert imports == []

    def test_no_forbidden_imports_anywhere(self):
        import execution_gateway.reconciliation_contracts as c
        import execution_gateway.reconciliation_engine as e
        import execution_gateway.reconciliation_precondition_error as p
        for module in (c, e, p):
            imports = self._module_imports(module)
            violations = [i for i in imports if any(f in i.lower() for f in self._FORBIDDEN_SUBSTRINGS)]
            assert violations == [], f"{module.__name__}: {violations}"

    def test_no_repair_or_mutation_vocabulary_as_code(self):
        import ast
        import inspect
        import execution_gateway.reconciliation_engine as module
        tree = ast.parse(inspect.getsource(module))
        banned = ("cancel", "repair", "remediate", "create_order", "close_position", "resize")
        identifiers = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                identifiers.append(node.name)
            elif isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.append(node.attr)
        offenders = [i for i in identifiers if any(b in i.lower() for b in banned)]
        assert offenders == []

    def test_no_clock_or_environment_access(self):
        import inspect
        import execution_gateway.reconciliation_engine as module
        src = inspect.getsource(module)
        for banned in ("time.time", "datetime.now", "os.environ", "open(", "socket."):
            assert banned not in src

    def test_reconcile_is_pure_same_inputs_same_output_no_side_effects(self):
        expected = _exp_state(scope=_scope(), positions=(_exp_position(),))
        observed = _snapshot(positions=(_obs_position(),))
        before_expected = expected
        before_observed = observed
        result1 = reconcile_execution_state(expected=expected, observed=observed)
        result2 = reconcile_execution_state(expected=expected, observed=observed)
        assert result1 == result2
        assert expected == before_expected
        assert observed == before_observed

    def test_rejects_non_expected_execution_state(self):
        with pytest.raises(TypeError, match="expected must be ExpectedExecutionState"):
            reconcile_execution_state(expected=object(), observed=_snapshot())

    def test_rejects_non_exchange_state_snapshot(self):
        with pytest.raises(TypeError, match="observed must be ExchangeStateSnapshot"):
            reconcile_execution_state(expected=_exp_state(), observed=object())
