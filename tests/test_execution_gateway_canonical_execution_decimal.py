import inspect
from decimal import Decimal, InvalidOperation

import pytest

import execution_gateway
import execution_gateway.canonical_execution_decimal as _module
from execution_gateway.canonical_execution_decimal import canonical_execution_decimal
from execution_gateway.execution_request_not_supported_error import ExecutionRequestNotSupportedError


class TestImport:
    def test_direct_import(self):
        from execution_gateway.canonical_execution_decimal import canonical_execution_decimal as f
        assert f is canonical_execution_decimal

    def test_public_import(self):
        assert hasattr(execution_gateway, "canonical_execution_decimal")
        assert execution_gateway.canonical_execution_decimal is canonical_execution_decimal

    def test_in_all(self):
        assert "canonical_execution_decimal" in execution_gateway.__all__


# ---------------------------------------------------------------------------
# Semántica exacta (ADR-014 Decisión 2): Decimal(str(value)), nada más.
# ---------------------------------------------------------------------------

class TestCanonicalSemantics:
    @pytest.mark.parametrize("value", [0.1, 0.01, 0.001, 1.1, 0.3])
    def test_matches_decimal_of_str_exactly(self, value):
        assert canonical_execution_decimal(value) == Decimal(str(value))

    @pytest.mark.parametrize("value", [0.1, 0.01, 0.001, 1.1, 0.3])
    def test_representation_matches_str_value_literally(self, value):
        # No basta con `==` -- Decimal(0.1) (binario) también termina
        # siendo aritméticamente comparable a algo, pero su *representación*
        # difiere de Decimal(str(0.1)). Se fija el string exacto.
        assert str(canonical_execution_decimal(value)) == str(value)

    def test_does_not_introduce_binary_floating_point_error(self):
        # Decimal(0.1) (sin str) produce un valor ligeramente distinto de
        # Decimal("0.1") -- exactamente el error que ADR-014 prohíbe.
        assert canonical_execution_decimal(0.1) != Decimal(0.1)

    def test_zero_is_preserved(self):
        assert canonical_execution_decimal(0.0) == Decimal("0.0")

    def test_negative_value_preserved_literally(self):
        assert canonical_execution_decimal(-1.5) == Decimal("-1.5")

    def test_large_value_without_scientific_notation(self):
        result = canonical_execution_decimal(1e16)
        assert format(result, "f") == "10000000000000000"

    def test_small_value_without_scientific_notation(self):
        result = canonical_execution_decimal(1e-8)
        assert format(result, "f") == "0.00000001"


# ---------------------------------------------------------------------------
# Rechazo de valores no finitos (idéntico a la implementación reemplazada).
# ---------------------------------------------------------------------------

class TestNonFiniteRejection:
    def test_positive_infinity_rejected(self):
        with pytest.raises(ExecutionRequestNotSupportedError):
            canonical_execution_decimal(float("inf"))

    def test_negative_infinity_rejected(self):
        with pytest.raises(ExecutionRequestNotSupportedError):
            canonical_execution_decimal(float("-inf"))

    def test_nan_rejected(self):
        with pytest.raises(ExecutionRequestNotSupportedError):
            canonical_execution_decimal(float("nan"))

    def test_rejection_message_is_non_empty(self):
        with pytest.raises(ExecutionRequestNotSupportedError) as exc_info:
            canonical_execution_decimal(float("nan"))
        assert str(exc_info.value)


# ---------------------------------------------------------------------------
# Frontera de input: ni más amplia ni más angosta que la que
# `ExecutionRequest.quantity`/`price` ya aceptan hoy -- sin isinstance
# nuevo. Documenta el comportamiento YA EXISTENTE frente a tipos que el
# Port nunca declaró soportar; ninguna garantía nueva se decide aquí.
# ---------------------------------------------------------------------------

class TestInputContractMatchesExistingBoundary:
    def test_int_accepted_like_a_whole_valued_float(self):
        assert canonical_execution_decimal(5) == Decimal("5")

    def test_bool_true_raises_invalid_operation(self):
        # math.isfinite(True) es True (bool es subclase de int), pero
        # Decimal(str(True)) == Decimal("True") no es sintaxis numérica
        # válida. Comportamiento preexistente, sin cambio en Hito 3.92.
        with pytest.raises(InvalidOperation):
            canonical_execution_decimal(True)

    def test_bool_false_raises_invalid_operation(self):
        with pytest.raises(InvalidOperation):
            canonical_execution_decimal(False)

    def test_decimal_input_round_trips_without_altering_value(self):
        assert canonical_execution_decimal(Decimal("0.1")) == Decimal("0.1")

    def test_string_input_raises_type_error_before_any_conversion(self):
        # math.isfinite() exige un número real; un str nunca llega a
        # Decimal(str(value)).
        with pytest.raises(TypeError):
            canonical_execution_decimal("0.1")

    def test_none_raises_type_error(self):
        with pytest.raises(TypeError):
            canonical_execution_decimal(None)


# ---------------------------------------------------------------------------
# Fixtures discriminantes para G2 M3 (round antes de convertir) y M4
# (quantize después de convertir) -- cada test fija su propia precondición
# explícita del ataque antes de exigir el resultado canónico.
# ---------------------------------------------------------------------------

class TestMutationDiscriminatingFixtures:
    _HIGH_PRECISION_VALUE = 1.123456789012345

    def test_high_precision_value_would_be_altered_by_eight_decimal_rounding(self):
        exact = canonical_execution_decimal(self._HIGH_PRECISION_VALUE)
        rounded_then_converted = Decimal(str(round(self._HIGH_PRECISION_VALUE, 8)))
        # Precondición explícita: si redondear a 8 decimales NO alterara
        # este valor, la fixture no discriminaría un mutante M3.
        assert exact != rounded_then_converted
        assert exact == Decimal(str(self._HIGH_PRECISION_VALUE))

    def test_high_precision_value_would_be_altered_by_eight_decimal_quantize(self):
        exact = canonical_execution_decimal(self._HIGH_PRECISION_VALUE)
        quantized = exact.quantize(Decimal("0.00000001"))
        assert exact != quantized
        assert exact == Decimal(str(self._HIGH_PRECISION_VALUE))

    def test_non_diadic_value_would_be_altered_by_direct_decimal_construction(self):
        # Precondición explícita de M1/M2: Decimal(0.1) (constructor
        # binario directo) difiere de Decimal(str(0.1)).
        assert Decimal(0.1) != Decimal(str(0.1))
        assert canonical_execution_decimal(0.1) == Decimal(str(0.1))


# ---------------------------------------------------------------------------
# Pureza: determinista, sin reloj/entorno/red/storage/estado mutable.
# ---------------------------------------------------------------------------

class TestPurity:
    def test_same_float_always_produces_same_decimal(self):
        assert canonical_execution_decimal(0.1) == canonical_execution_decimal(0.1)
        assert canonical_execution_decimal(0.1) is not canonical_execution_decimal(0.1)

    def test_float_round_trip_after_conversion_is_a_mathematical_no_op(self):
        # G2-M6 (Hito 3.92): "el adapter aplica un float() extra tras
        # canonical" resultó SOBREVIVE en la batería de mutación --
        # confirmado como EQUIVALENTE, no como hueco de cobertura.
        # `str(float)` en Python garantiza la representación decimal más
        # corta que reconstruye ese mismo float exactamente (desde Python
        # 3.1); por lo tanto Decimal(str(float(canonical_execution_decimal(v))))
        # es indistinguible de canonical_execution_decimal(v) para
        # cualquier float finito -- no existe fixture que discrimine esta
        # mutación porque no altera ningún valor real, mismo patrón que
        # N35b en Hito 3.91 (`.normalize()` preserva el valor).
        for value in (0.1, 0.01, 0.001, 1.1, 0.3, 123456789.123, 1e-8, 1e16):
            exact = canonical_execution_decimal(value)
            round_tripped = Decimal(str(float(exact)))
            assert exact == round_tripped

    def test_no_clock_or_environment_or_network_access(self):
        src = inspect.getsource(_module)
        for banned in ("time.time", "datetime.now", "os.environ", "open(", "socket.", "random.", "urllib"):
            assert banned not in src

    def test_module_has_no_mutable_global_state(self):
        for name, value in vars(_module).items():
            if name.startswith("_") and not name.startswith("__"):
                assert not isinstance(value, (list, dict, set)), (
                    f"{name} is mutable module-level state"
                )
