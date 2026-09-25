import dataclasses
from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.economic_comparison_contracts import (
    EconomicComparisonResult,
    EconomicDivergence,
    EconomicOrderTypeMismatch,
    EconomicPriceMismatch,
    EconomicQuantityMismatch,
    EconomicReduceOnlyMismatch,
    EconomicSideMismatch,
    EconomicSymbolMismatch,
)
from execution_gateway.execution_identity_contracts import ExecutionOrderId

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


class TestImport:
    @pytest.mark.parametrize("name", [
        "EconomicDivergence", "EconomicSymbolMismatch", "EconomicSideMismatch",
        "EconomicOrderTypeMismatch", "EconomicQuantityMismatch", "EconomicPriceMismatch",
        "EconomicReduceOnlyMismatch", "EconomicComparisonResult",
    ])
    def test_importable_from_package_and_in_all(self, name):
        assert hasattr(execution_gateway, name)
        assert name in execution_gateway.__all__


class TestEconomicDivergenceMarker:
    def test_never_instantiated_directly(self):
        # Mismo patrón que Divergence (reconciliation_contracts.py) y
        # LocalFact/RemoteFact/ObservedFact -- marcador puro.
        sym = EconomicSymbolMismatch(
            execution_order_id=_OID, attempted_symbol="BTCUSDT", observed_symbol="ETHUSDT",
        )
        assert isinstance(sym, EconomicDivergence)
        assert type(sym) is not EconomicDivergence

    def test_all_six_are_subclasses(self):
        for cls in (
            EconomicSymbolMismatch, EconomicSideMismatch, EconomicOrderTypeMismatch,
            EconomicQuantityMismatch, EconomicPriceMismatch, EconomicReduceOnlyMismatch,
        ):
            assert issubclass(cls, EconomicDivergence)

    def test_no_identity_mismatch_type_exists(self):
        # ADR-014 D9/D11/D19: identidad cruzada es precondición fail-closed,
        # NUNCA una divergencia -- no debe existir ningún tipo de esta
        # familia para representarla.
        import execution_gateway.economic_comparison_contracts as module
        names = {n for n, v in vars(module).items() if isinstance(v, type)}
        for forbidden in ("IdentityMismatch", "ExecutionOrderIdMismatch"):
            assert forbidden not in names


class TestEconomicSymbolMismatch:
    def test_constructs_validly(self):
        d = EconomicSymbolMismatch(
            execution_order_id=_OID, attempted_symbol="BTCUSDT", observed_symbol="ETHUSDT",
        )
        assert d.execution_order_id is _OID
        assert d.attempted_symbol == "BTCUSDT"
        assert d.observed_symbol == "ETHUSDT"

    def test_is_frozen(self):
        d = EconomicSymbolMismatch(
            execution_order_id=_OID, attempted_symbol="BTCUSDT", observed_symbol="ETHUSDT",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            d.attempted_symbol = "X"

    @pytest.mark.parametrize("bad", [None, 123, True, object()])
    def test_rejects_non_execution_order_id(self, bad):
        with pytest.raises(TypeError):
            EconomicSymbolMismatch(execution_order_id=bad, attempted_symbol="A", observed_symbol="B")

    @pytest.mark.parametrize("field", ["attempted_symbol", "observed_symbol"])
    def test_rejects_empty_string(self, field):
        kwargs = dict(execution_order_id=_OID, attempted_symbol="A", observed_symbol="B")
        kwargs[field] = ""
        with pytest.raises(ValueError):
            EconomicSymbolMismatch(**kwargs)

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicSymbolMismatch)}
        assert names == {"execution_order_id", "attempted_symbol", "observed_symbol"}


class TestEconomicSideMismatch:
    def test_constructs_validly(self):
        d = EconomicSideMismatch(execution_order_id=_OID, attempted_side="buy", observed_side="sell")
        assert d.attempted_side == "buy"
        assert d.observed_side == "sell"

    @pytest.mark.parametrize("bad", ["Buy", "long", "", None, 1])
    def test_rejects_invalid_side(self, bad):
        with pytest.raises((TypeError, ValueError)):
            EconomicSideMismatch(execution_order_id=_OID, attempted_side=bad, observed_side="sell")

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicSideMismatch)}
        assert names == {"execution_order_id", "attempted_side", "observed_side"}


class TestEconomicOrderTypeMismatch:
    def test_constructs_validly(self):
        d = EconomicOrderTypeMismatch(
            execution_order_id=_OID, attempted_order_type="limit", observed_order_type="market",
        )
        assert d.attempted_order_type == "limit"
        assert d.observed_order_type == "market"

    @pytest.mark.parametrize("bad", ["Limit", "stop", "", None])
    def test_rejects_invalid_order_type(self, bad):
        with pytest.raises((TypeError, ValueError)):
            EconomicOrderTypeMismatch(
                execution_order_id=_OID, attempted_order_type=bad, observed_order_type="market",
            )

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicOrderTypeMismatch)}
        assert names == {"execution_order_id", "attempted_order_type", "observed_order_type"}


class TestEconomicQuantityMismatch:
    def test_constructs_validly(self):
        d = EconomicQuantityMismatch(
            execution_order_id=_OID, attempted_quantity=Decimal("10"), observed_quantity=Decimal("9"),
        )
        assert d.attempted_quantity == Decimal("10")
        assert d.observed_quantity == Decimal("9")

    @pytest.mark.parametrize("bad", [None, 1, 1.5, "1", True, object()])
    def test_rejects_non_decimal(self, bad):
        with pytest.raises(TypeError):
            EconomicQuantityMismatch(
                execution_order_id=_OID, attempted_quantity=bad, observed_quantity=Decimal("1"),
            )

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
    def test_rejects_non_finite(self, bad):
        with pytest.raises(ValueError):
            EconomicQuantityMismatch(
                execution_order_id=_OID, attempted_quantity=bad, observed_quantity=Decimal("1"),
            )

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicQuantityMismatch)}
        assert names == {"execution_order_id", "attempted_quantity", "observed_quantity"}


class TestEconomicPriceMismatch:
    def test_constructs_validly_both_decimal(self):
        d = EconomicPriceMismatch(
            execution_order_id=_OID, attempted_price=Decimal("100"), observed_price=Decimal("101"),
        )
        assert d.attempted_price == Decimal("100")
        assert d.observed_price == Decimal("101")

    def test_constructs_validly_shape_mismatch(self):
        # MARKET local (None) vs LIMIT remoto (Decimal) -- forma de
        # mismatch legítima (ADR-014 D19).
        d = EconomicPriceMismatch(
            execution_order_id=_OID, attempted_price=None, observed_price=Decimal("101"),
        )
        assert d.attempted_price is None
        assert d.observed_price == Decimal("101")

    @pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity")])
    def test_rejects_non_finite_when_present(self, bad):
        with pytest.raises(ValueError):
            EconomicPriceMismatch(execution_order_id=_OID, attempted_price=bad, observed_price=None)

    @pytest.mark.parametrize("bad", [1, "100", True, object()])
    def test_rejects_non_decimal_when_present(self, bad):
        with pytest.raises(TypeError):
            EconomicPriceMismatch(execution_order_id=_OID, attempted_price=bad, observed_price=None)

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicPriceMismatch)}
        assert names == {"execution_order_id", "attempted_price", "observed_price"}


class TestEconomicReduceOnlyMismatch:
    def test_constructs_validly(self):
        d = EconomicReduceOnlyMismatch(
            execution_order_id=_OID, attempted_reduce_only=False, observed_reduce_only=True,
        )
        assert d.attempted_reduce_only is False
        assert d.observed_reduce_only is True

    @pytest.mark.parametrize("bad", [0, 1, None, "false"])
    def test_rejects_non_bool(self, bad):
        with pytest.raises(TypeError):
            EconomicReduceOnlyMismatch(
                execution_order_id=_OID, attempted_reduce_only=bad, observed_reduce_only=True,
            )

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicReduceOnlyMismatch)}
        assert names == {"execution_order_id", "attempted_reduce_only", "observed_reduce_only"}


class TestEconomicComparisonResult:
    def test_empty_is_matched(self):
        result = EconomicComparisonResult(divergences=())
        assert result.is_matched is True

    def test_non_empty_is_not_matched(self):
        d = EconomicSymbolMismatch(execution_order_id=_OID, attempted_symbol="A", observed_symbol="B")
        result = EconomicComparisonResult(divergences=(d,))
        assert result.is_matched is False

    def test_is_matched_is_derived_no_settable_field(self):
        result = EconomicComparisonResult(divergences=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.is_matched = False

    def test_is_frozen(self):
        result = EconomicComparisonResult(divergences=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.divergences = (1,)

    def test_rejects_non_tuple_divergences(self):
        with pytest.raises(TypeError):
            EconomicComparisonResult(divergences=[])

    def test_rejects_non_divergence_elements(self):
        with pytest.raises(TypeError):
            EconomicComparisonResult(divergences=(object(),))

    def test_preserves_multiple_divergences_and_order(self):
        d1 = EconomicSymbolMismatch(execution_order_id=_OID, attempted_symbol="A", observed_symbol="B")
        d2 = EconomicSideMismatch(execution_order_id=_OID, attempted_side="buy", observed_side="sell")
        result = EconomicComparisonResult(divergences=(d1, d2))
        assert result.divergences == (d1, d2)
        assert result.is_matched is False

    def test_field_set(self):
        names = {f.name for f in dataclasses.fields(EconomicComparisonResult)}
        assert names == {"divergences"}
