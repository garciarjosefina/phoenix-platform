import ast
import inspect
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.economic_comparator as _comparator_module
from execution_gateway.economic_comparator import compare_attempted_order_to_observed_economics
from execution_gateway.economic_comparison_contracts import (
    EconomicOrderTypeMismatch,
    EconomicPriceMismatch,
    EconomicQuantityMismatch,
    EconomicReduceOnlyMismatch,
    EconomicSideMismatch,
    EconomicSymbolMismatch,
)
from execution_gateway.economic_comparison_precondition_error import (
    EconomicComparisonPreconditionError,
)
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.execution_ledger_event_contracts import OrderSubmissionAttempted
from execution_gateway.observed_order_economics_contracts import ObservedOrderEconomics
from execution_gateway.observed_order_economics_projections import (
    project_closed_order_to_observed_economics,
    project_open_order_to_observed_economics,
)
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderFoundOpen

_OID = ExecutionOrderId(value="ord_" + "a" * 32)
_OID_Y = ExecutionOrderId(value="ord_" + "b" * 32)


def _attempted(**overrides):
    defaults = dict(
        execution_order_id=_OID, symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("1"), price=Decimal("100"),
    )
    defaults.update(overrides)
    return OrderSubmissionAttempted(**defaults)


def _observed(**overrides):
    defaults = dict(
        execution_order_id=_OID, symbol="BTCUSDT", side="buy", order_type="limit",
        quantity=Decimal("1"), price=Decimal("100"), reduce_only=False,
    )
    defaults.update(overrides)
    return ObservedOrderEconomics(**defaults)


def _open_order(**overrides):
    defaults = dict(
        execution_order_id=_OID, exchange_order_id="BYBIT-OPEN-1", symbol="BTCUSDT",
        side="buy", order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("0"),
        filled_value=Decimal("0"), remote_status="new", reduce_only=False,
        server_time_ms=1000, remote_created_time_ms=900, remote_updated_time_ms=900,
        price=Decimal("100"), average_price=None, reject_reason=None,
    )
    defaults.update(overrides)
    return BybitRealtimeOrderFoundOpen(**defaults)


def _closed_order(**overrides):
    defaults = dict(
        execution_order_id=_OID, exchange_order_id="BYBIT-CLOSED-1", symbol="BTCUSDT",
        side="buy", order_type="limit", quantity=Decimal("1"), filled_quantity=Decimal("1"),
        filled_value=Decimal("100"), remote_status="filled", reduce_only=False,
        server_time_ms=2000, remote_created_time_ms=900, remote_updated_time_ms=1900,
        price=Decimal("100"), average_price=Decimal("99.5"), cancel_type=None,
        reject_reason=None,
    )
    defaults.update(overrides)
    return BybitOrderHistoryOrderFound(**defaults)


def _compare(attempted=None, observed=None):
    return compare_attempted_order_to_observed_economics(
        attempted=attempted if attempted is not None else _attempted(),
        observed=observed if observed is not None else _observed(),
    )


class TestImport:
    def test_importable_from_package_and_in_all(self):
        assert hasattr(execution_gateway, "compare_attempted_order_to_observed_economics")
        assert "compare_attempted_order_to_observed_economics" in execution_gateway.__all__

    def test_is_module_function(self):
        assert (
            execution_gateway.compare_attempted_order_to_observed_economics
            is compare_attempted_order_to_observed_economics
        )


class TestInputTypeValidation:
    def test_rejects_non_attempted(self):
        with pytest.raises(TypeError, match="attempted must be OrderSubmissionAttempted"):
            compare_attempted_order_to_observed_economics(attempted=object(), observed=_observed())

    def test_rejects_non_observed(self):
        with pytest.raises(TypeError, match="observed must be ObservedOrderEconomics"):
            compare_attempted_order_to_observed_economics(attempted=_attempted(), observed=object())

    def test_rejects_bybit_open_type_directly(self):
        # ADR-014, Resolución del STOP, Decisión 1: el comparador NUNCA
        # acepta tipos Bybit* directamente.
        with pytest.raises(TypeError):
            compare_attempted_order_to_observed_economics(attempted=_attempted(), observed=_open_order())

    def test_rejects_bybit_closed_type_directly(self):
        with pytest.raises(TypeError):
            compare_attempted_order_to_observed_economics(attempted=_attempted(), observed=_closed_order())


class TestIdentityFailClosed:
    def test_cross_identity_raises_precondition_error(self):
        with pytest.raises(EconomicComparisonPreconditionError):
            _compare(observed=_observed(execution_order_id=_OID_Y))

    def test_cross_identity_never_returns_a_result(self):
        try:
            _compare(observed=_observed(execution_order_id=_OID_Y))
            assert False, "expected EconomicComparisonPreconditionError"
        except EconomicComparisonPreconditionError:
            pass

    def test_cross_identity_is_not_confused_with_economic_mismatch(self):
        # Ninguna divergencia de la familia debe aparecer -- es un error,
        # no un resultado con divergencias (ADR-014 D9/D11/D19).
        with pytest.raises(EconomicComparisonPreconditionError) as exc_info:
            _compare(observed=_observed(execution_order_id=_OID_Y))
        assert not hasattr(exc_info.value, "divergences")

    def test_same_identity_by_value_is_accepted(self):
        # ExecutionOrderId compara por valor (frozen dataclass) -- dos
        # instancias distintas con el mismo value son la misma identidad.
        same_value = ExecutionOrderId(value=_OID.value)
        result = _compare(observed=_observed(execution_order_id=same_value))
        assert result.is_matched is True


# ---------------------------------------------------------------------------
# Casos de MATCH (ADR-014 D17) -- construidos vía las proyecciones reales,
# no directamente sobre ObservedOrderEconomics, para ejercer el pipeline
# completo lookup -> proyección -> comparador.
# ---------------------------------------------------------------------------

class TestMatchCases:
    def test_limit_open_new(self):
        attempted = _attempted(order_type="limit", price=Decimal("100"))
        observed = project_open_order_to_observed_economics(
            open_order=_open_order(order_type="limit", price=Decimal("100"), remote_status="new")
        )
        assert _compare(attempted, observed).is_matched is True

    def test_open_partially_filled(self):
        attempted = _attempted(quantity=Decimal("1"), price=Decimal("100"))
        observed = project_open_order_to_observed_economics(
            open_order=_open_order(
                quantity=Decimal("1"), price=Decimal("100"),
                remote_status="partially_filled", filled_quantity=Decimal("0.4"),
                filled_value=Decimal("40"), average_price=Decimal("100"),
            )
        )
        result = _compare(attempted, observed)
        assert result.is_matched is True

    def test_market_closed_filled(self):
        attempted = _attempted(order_type="market", price=None)
        observed = project_closed_order_to_observed_economics(
            closed_order=_closed_order(
                order_type="market", price=None, remote_status="filled",
                filled_quantity=Decimal("1"), filled_value=Decimal("6000"),
                average_price=Decimal("6000"),
            )
        )
        assert _compare(attempted, observed).is_matched is True

    def test_open_market_partially_filled_ignores_average_price(self):
        # Auditoría 3.91: una orden MARKET puede seguir "abierta" como
        # partially_filled -- filled_quantity>0 exige average_price!=None
        # por invariante propia de BybitRealtimeOrderFoundOpen, mientras
        # `price` sigue siendo None por ser MARKET. El comparador debe
        # seguir viendo price=None en ambos lados (ADR-014 D4/F6), nunca
        # sustituirlo por average_price.
        attempted = _attempted(order_type="market", price=None)
        observed = project_open_order_to_observed_economics(
            open_order=_open_order(
                order_type="market", price=None, remote_status="partially_filled",
                filled_quantity=Decimal("0.3"), filled_value=Decimal("300"),
                average_price=Decimal("1000"),
            )
        )
        result = _compare(attempted, observed)
        assert result.is_matched is True

    def test_closed_cancelled(self):
        attempted = _attempted()
        observed = project_closed_order_to_observed_economics(
            closed_order=_closed_order(
                remote_status="cancelled", filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=None, cancel_type="CancelByUser",
            )
        )
        assert _compare(attempted, observed).is_matched is True

    def test_closed_rejected(self):
        attempted = _attempted()
        observed = project_closed_order_to_observed_economics(
            closed_order=_closed_order(
                remote_status="rejected", filled_quantity=Decimal("0"),
                filled_value=Decimal("0"), average_price=None,
                reject_reason="EC_InsufficientBalance",
            )
        )
        assert _compare(attempted, observed).is_matched is True


# ---------------------------------------------------------------------------
# Mismatch aislado por dimensión (ADR-014 D18) -- cada uno produce
# EXACTAMENTE una divergencia, de su tipo específico.
# ---------------------------------------------------------------------------

class TestIsolatedMismatchPerDimension:
    def test_symbol_mismatch_only(self):
        result = _compare(observed=_observed(symbol="ETHUSDT"))
        assert len(result.divergences) == 1
        assert isinstance(result.divergences[0], EconomicSymbolMismatch)
        assert result.divergences[0].attempted_symbol == "BTCUSDT"
        assert result.divergences[0].observed_symbol == "ETHUSDT"

    def test_symbol_is_case_sensitive(self):
        # Auditoría 3.91: la comparación de symbol es literal-exacta
        # (ADR-014 D6) -- "BTCUSDT" y "btcusdt" NO son el mismo símbolo
        # para el comparador, aunque lo fueran para un humano.
        attempted = _attempted(symbol="BTCUSDT")
        result = _compare(attempted, observed=_observed(symbol="btcusdt"))
        assert result.is_matched is False
        assert isinstance(result.divergences[0], EconomicSymbolMismatch)

    def test_side_mismatch_only(self):
        result = _compare(observed=_observed(side="sell"))
        assert len(result.divergences) == 1
        assert isinstance(result.divergences[0], EconomicSideMismatch)

    def test_order_type_and_price_mismatch_together(self):
        # No se puede aislar order_type sin afectar price: LIMIT local
        # (price=100) vs MARKET remoto (price=None) diverge en AMBAS
        # dimensiones por construcción -- documentado explícitamente
        # (ADR-014 D19, brief §15). Se verifica que ambas y sólo esas dos
        # aparecen.
        result = _compare(observed=_observed(order_type="market", price=None))
        kinds = {type(d) for d in result.divergences}
        assert kinds == {EconomicOrderTypeMismatch, EconomicPriceMismatch}
        assert len(result.divergences) == 2

    def test_quantity_mismatch_only(self):
        result = _compare(observed=_observed(quantity=Decimal("2")))
        assert len(result.divergences) == 1
        assert isinstance(result.divergences[0], EconomicQuantityMismatch)
        assert result.divergences[0].attempted_quantity == Decimal("1")
        assert result.divergences[0].observed_quantity == Decimal("2")

    def test_limit_price_mismatch_only(self):
        result = _compare(observed=_observed(price=Decimal("101")))
        assert len(result.divergences) == 1
        assert isinstance(result.divergences[0], EconomicPriceMismatch)
        assert result.divergences[0].attempted_price == Decimal("100")
        assert result.divergences[0].observed_price == Decimal("101")

    def test_reduce_only_mismatch_only(self):
        result = _compare(observed=_observed(reduce_only=True))
        assert len(result.divergences) == 1
        assert isinstance(result.divergences[0], EconomicReduceOnlyMismatch)
        assert result.divergences[0].attempted_reduce_only is False
        assert result.divergences[0].observed_reduce_only is True

    def test_reduce_only_false_matches_constant(self):
        result = _compare(observed=_observed(reduce_only=False))
        assert result.is_matched is True


class TestMultiMismatch:
    def test_all_six_dimensions_diverge(self):
        attempted = _attempted(
            symbol="BTCUSDT", side="buy", order_type="limit",
            quantity=Decimal("1"), price=Decimal("100"),
        )
        observed = _observed(
            symbol="ETHUSDT", side="sell", order_type="market",
            quantity=Decimal("2"), price=None, reduce_only=True,
        )
        result = _compare(attempted, observed)
        assert len(result.divergences) == 6
        kinds = [type(d) for d in result.divergences]
        assert kinds == [
            EconomicSymbolMismatch, EconomicSideMismatch, EconomicOrderTypeMismatch,
            EconomicQuantityMismatch, EconomicPriceMismatch, EconomicReduceOnlyMismatch,
        ]
        assert result.is_matched is False

    def test_three_dimensions_diverge_none_lost_none_duplicated(self):
        result = _compare(observed=_observed(symbol="ETHUSDT", quantity=Decimal("5"), reduce_only=True))
        kinds = [type(d) for d in result.divergences]
        assert kinds == [EconomicSymbolMismatch, EconomicQuantityMismatch, EconomicReduceOnlyMismatch]
        assert len(kinds) == len(set(kinds)) == 3

    def test_order_is_stable_regardless_of_which_combination_mismatches(self):
        # symbol, side, order_type, quantity, price, reduce_only -- fijo
        # (ADR-014 D2/D12/D18), independientemente de qué subconjunto
        # diverja.
        result_a = _compare(observed=_observed(reduce_only=True, side="sell"))
        assert [type(d) for d in result_a.divergences] == [EconomicSideMismatch, EconomicReduceOnlyMismatch]

        result_b = _compare(observed=_observed(quantity=Decimal("9"), symbol="ETHUSDT"))
        assert [type(d) for d in result_b.divergences] == [EconomicSymbolMismatch, EconomicQuantityMismatch]


# ---------------------------------------------------------------------------
# Invariancia de metadata (brief §13) -- variar SOLO campos de evolución/
# metadata en la fuente remota real (antes de proyectar) no debe alterar
# el veredicto.
# ---------------------------------------------------------------------------

class TestMetadataInvariance:
    @pytest.mark.parametrize("overrides", [
        dict(exchange_order_id="ANY-OTHER-ID"),
        dict(server_time_ms=1),
        dict(remote_created_time_ms=1, remote_updated_time_ms=1),
        dict(remote_status="partially_filled", filled_quantity=Decimal("0.9"),
             filled_value=Decimal("90"), average_price=Decimal("100")),
    ])
    def test_open_metadata_variation_still_matches(self, overrides):
        attempted = _attempted()
        observed = project_open_order_to_observed_economics(open_order=_open_order(**overrides))
        assert _compare(attempted, observed).is_matched is True

    @pytest.mark.parametrize("overrides", [
        dict(exchange_order_id="ANY-OTHER-ID"),
        dict(server_time_ms=1),
        dict(remote_created_time_ms=1, remote_updated_time_ms=1),
        dict(average_price=Decimal("50")),
        dict(remote_status="cancelled", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
             average_price=None, cancel_type="CancelByUser"),
        dict(remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
             average_price=None, reject_reason="EC_InsufficientBalance"),
    ])
    def test_closed_metadata_variation_still_matches(self, overrides):
        attempted = _attempted()
        observed = project_closed_order_to_observed_economics(closed_order=_closed_order(**overrides))
        assert _compare(attempted, observed).is_matched is True


# ---------------------------------------------------------------------------
# Adversariales (ADR-014 D19)
# ---------------------------------------------------------------------------

class TestAdversarial:
    def test_partial_fill_with_equal_original_economics_matches(self):
        attempted = _attempted(quantity=Decimal("10"))
        observed = project_open_order_to_observed_economics(
            open_order=_open_order(
                quantity=Decimal("10"), remote_status="partially_filled",
                filled_quantity=Decimal("4"), filled_value=Decimal("400"),
                average_price=Decimal("100"),
            )
        )
        assert _compare(attempted, observed).is_matched is True

    def test_filled_with_average_price_different_from_limit_price_matches(self):
        attempted = _attempted(price=Decimal("100"))
        observed = project_closed_order_to_observed_economics(
            closed_order=_closed_order(
                price=Decimal("100"), average_price=Decimal("97.25"),
                remote_status="filled", filled_quantity=Decimal("1"), filled_value=Decimal("97.25"),
            )
        )
        assert _compare(attempted, observed).is_matched is True

    def test_different_timestamps_match(self):
        attempted = _attempted()
        o1 = project_open_order_to_observed_economics(
            open_order=_open_order(server_time_ms=1, remote_created_time_ms=1, remote_updated_time_ms=1)
        )
        o2 = project_open_order_to_observed_economics(
            open_order=_open_order(server_time_ms=999999, remote_created_time_ms=1, remote_updated_time_ms=999999)
        )
        assert _compare(attempted, o1) == _compare(attempted, o2)
        assert _compare(attempted, o1).is_matched is True

    def test_arbitrary_exchange_order_id_matches(self):
        attempted = _attempted()
        o1 = project_open_order_to_observed_economics(open_order=_open_order(exchange_order_id="AAA"))
        o2 = project_open_order_to_observed_economics(open_order=_open_order(exchange_order_id="ZZZ"))
        assert _compare(attempted, o1) == _compare(attempted, o2)
        assert _compare(attempted, o1).is_matched is True

    def test_market_local_vs_limit_remote_reports_both_order_type_and_price(self):
        attempted = _attempted(order_type="market", price=None)
        observed = _observed(order_type="limit", price=Decimal("100"))
        result = _compare(attempted, observed)
        kinds = {type(d) for d in result.divergences}
        assert kinds == {EconomicOrderTypeMismatch, EconomicPriceMismatch}

    def test_reduce_only_true_mismatches(self):
        result = _compare(observed=_observed(reduce_only=True))
        assert result.is_matched is False
        assert isinstance(result.divergences[0], EconomicReduceOnlyMismatch)

    def test_cross_identity_is_error_not_mismatch(self):
        with pytest.raises(EconomicComparisonPreconditionError):
            _compare(observed=_observed(execution_order_id=_OID_Y))


# ---------------------------------------------------------------------------
# Decimal
# ---------------------------------------------------------------------------

class TestDecimalSemantics:
    @pytest.mark.parametrize("value", ["0.1", "0.01", "0.001"])
    def test_non_diadic_values_match_when_equal(self, value):
        attempted = _attempted(quantity=Decimal(value))
        observed = _observed(quantity=Decimal(value))
        assert _compare(attempted, observed).is_matched is True

    @pytest.mark.parametrize("a,b", [("1", "1.0"), ("1", "1.000"), ("0.10", "0.1")])
    def test_equivalent_representations_match(self, a, b):
        attempted = _attempted(quantity=Decimal(a))
        observed = _observed(quantity=Decimal(b))
        assert _compare(attempted, observed).is_matched is True

    def test_non_diadic_mismatch_detected(self):
        attempted = _attempted(quantity=Decimal("0.1"))
        observed = _observed(quantity=Decimal("0.11"))
        result = _compare(attempted, observed)
        assert result.is_matched is False
        assert isinstance(result.divergences[0], EconomicQuantityMismatch)

    def test_price_equivalent_representations_match(self):
        attempted = _attempted(price=Decimal("100"))
        observed = _observed(price=Decimal("100.00"))
        assert _compare(attempted, observed).is_matched is True


# ---------------------------------------------------------------------------
# Determinismo y pureza
# ---------------------------------------------------------------------------

class TestDeterminism:
    def test_same_inputs_same_result(self):
        attempted = _attempted()
        observed = _observed(symbol="ETHUSDT")
        r1 = _compare(attempted, observed)
        r2 = _compare(attempted, observed)
        assert r1 == r2

    def test_inputs_not_mutated(self):
        attempted = _attempted()
        observed = _observed(symbol="ETHUSDT")
        snap_a = repr(attempted)
        snap_o = repr(observed)
        _compare(attempted, observed)
        assert repr(attempted) == snap_a
        assert repr(observed) == snap_o


class TestPurity:
    def _module_imports(self, module) -> list[str]:
        tree = ast.parse(inspect.getsource(module))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
        return names

    def test_module_imports(self):
        imports = self._module_imports(_comparator_module)
        assert set(imports) == {
            "execution_gateway.economic_comparison_contracts",
            "execution_gateway.economic_comparison_precondition_error",
            "execution_gateway.execution_ledger_event_contracts",
            "execution_gateway.observed_order_economics_contracts",
        }

    def test_no_forbidden_imports(self):
        imports = self._module_imports(_comparator_module)
        forbidden_substrings = ("bybit", "urllib", "http", "requests", "socket", "os")
        violations = [i for i in imports if any(f in i.lower() for f in forbidden_substrings)]
        assert violations == []

    def test_no_clock_or_environment_access(self):
        src = inspect.getsource(_comparator_module)
        for banned in ("time.time", "datetime.now", "os.environ", "open(", "socket.", "random."):
            assert banned not in src

    def test_no_float_in_source(self):
        src = inspect.getsource(_comparator_module)
        assert "float(" not in src

    def test_no_repair_or_recovery_vocabulary(self):
        tree = ast.parse(inspect.getsource(_comparator_module))
        identifiers = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                identifiers.append(node.name)
            elif isinstance(node, ast.Name):
                identifiers.append(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.append(node.attr)
        banned = ("resend", "retry", "halt", "escalate", "repair", "recover", "create_order", "cancel_order")
        offenders = [i for i in identifiers if any(b in i.lower() for b in banned)]
        assert offenders == []
