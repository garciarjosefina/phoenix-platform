import ast
import inspect
from decimal import Decimal

import pytest

import execution_gateway
import execution_gateway.observed_order_economics_projections as _projections_module
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.observed_order_economics_contracts import ObservedOrderEconomics
from execution_gateway.observed_order_economics_projections import (
    project_closed_order_to_observed_economics,
    project_open_order_to_observed_economics,
)
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import BybitRealtimeOrderFoundOpen

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


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


class TestImport:
    @pytest.mark.parametrize("name", [
        "project_open_order_to_observed_economics",
        "project_closed_order_to_observed_economics",
    ])
    def test_importable_from_package_and_in_all(self, name):
        assert hasattr(execution_gateway, name)
        assert name in execution_gateway.__all__


class TestProjectOpenOrder:
    def test_copies_the_seven_fields(self):
        result = project_open_order_to_observed_economics(open_order=_open_order())
        assert isinstance(result, ObservedOrderEconomics)
        assert result.execution_order_id is _OID
        assert result.symbol == "BTCUSDT"
        assert result.side == "buy"
        assert result.order_type == "limit"
        assert result.quantity == Decimal("1")
        assert result.price == Decimal("100")
        assert result.reduce_only is False

    def test_execution_order_id_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "b" * 32)
        result = project_open_order_to_observed_economics(
            open_order=_open_order(execution_order_id=marker)
        )
        assert result.execution_order_id is marker

    def test_copies_each_field_with_a_non_default_economy(self):
        # Auditoría adversarial 3.91, IMPORTANTE-1: `test_copies_the_seven_fields`
        # de arriba usa una economía (side="buy", symbol="BTCUSDT",
        # reduce_only=False) que coincide EXACTAMENTE con los valores que
        # una proyección defectuosa podría fijar como constante --
        # `side="buy"` fijo, `symbol="BTCUSDT"` fijo o `reduce_only=False`
        # fijo pasarían ese test sin copiar nada realmente. Aquí la
        # economía de origen es deliberadamente la contraria en cada
        # dimensión discriminable, con Decimal no triviales, y cada campo
        # se verifica contra su valor literal esperado -- nunca contra el
        # mismo diccionario de defaults que construyó el fixture.
        order = _open_order(
            symbol="ethusdt", side="sell", order_type="limit",
            quantity=Decimal("0.137"), price=Decimal("1234.567"), reduce_only=True,
        )
        result = project_open_order_to_observed_economics(open_order=order)
        assert result.symbol == "ethusdt"
        assert result.side == "sell"
        assert result.order_type == "limit"
        assert result.quantity == Decimal("0.137")
        assert result.price == Decimal("1234.567")
        assert result.reduce_only is True

    def test_symbol_with_padding_preserved_literal(self):
        # "ethusdt" (sin espacios) no discrimina un strip() indebido --
        # este fixture SÍ tiene espacios, así que una proyección que
        # aplicara strip() produciría un valor distinto y detectable.
        order = _open_order(symbol=" BTCUSDT ")
        assert project_open_order_to_observed_economics(open_order=order).symbol == " BTCUSDT "

    def test_market_price_projects_to_none(self):
        order = _open_order(order_type="market", price=None)
        assert project_open_order_to_observed_economics(open_order=order).price is None

    def test_rejects_wrong_type(self):
        with pytest.raises(TypeError):
            project_open_order_to_observed_economics(open_order=_closed_order())

    def test_rejects_non_bybit_type(self):
        with pytest.raises(TypeError):
            project_open_order_to_observed_economics(open_order=object())

    @pytest.mark.parametrize("overrides", [
        # Cada variante es internamente coherente con las invariantes
        # cruzadas de BybitRealtimeOrderFoundOpen -- sólo metadata/
        # evolución cambia, nunca las siete dimensiones económicas.
        dict(filled_quantity=Decimal("0.4"), filled_value=Decimal("40"),
             remote_status="partially_filled", average_price=Decimal("100")),
        dict(exchange_order_id="SOME-OTHER-EXCHANGE-ID"),
        dict(server_time_ms=999999),
        dict(remote_created_time_ms=1, remote_updated_time_ms=1),
        dict(remote_created_time_ms=1, remote_updated_time_ms=500000),
    ])
    def test_metadata_variation_does_not_affect_projection(self, overrides):
        # Auditoría 3.91: mismos siete campos económicos, metadata/
        # evolución arbitraria distinta -> proyección idéntica.
        baseline = project_open_order_to_observed_economics(open_order=_open_order())
        varied = project_open_order_to_observed_economics(
            open_order=_open_order(**overrides)
        )
        assert baseline == varied


class TestProjectClosedOrder:
    def test_copies_the_seven_fields(self):
        result = project_closed_order_to_observed_economics(closed_order=_closed_order())
        assert isinstance(result, ObservedOrderEconomics)
        assert result.execution_order_id is _OID
        assert result.symbol == "BTCUSDT"
        assert result.side == "buy"
        assert result.order_type == "limit"
        assert result.quantity == Decimal("1")
        assert result.price == Decimal("100")
        assert result.reduce_only is False

    def test_execution_order_id_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "c" * 32)
        result = project_closed_order_to_observed_economics(
            closed_order=_closed_order(execution_order_id=marker)
        )
        assert result.execution_order_id is marker

    def test_copies_each_field_with_a_non_default_economy(self):
        # Auditoría adversarial 3.91, IMPORTANTE-1: mismo razonamiento que
        # en OPEN -- una proyección con `symbol="BTCUSDT"` fijo o
        # `reduce_only=False` fijo pasaría `test_copies_the_seven_fields`
        # sin copiar nada. Economía deliberadamente distinta en cada
        # dimensión, verificada campo por campo.
        order = _closed_order(
            symbol="ethusdt", side="sell", order_type="limit",
            quantity=Decimal("0.137"), price=Decimal("1234.567"), reduce_only=True,
            filled_quantity=Decimal("0.137"), filled_value=Decimal("169.1"),
            remote_status="filled", average_price=Decimal("1234.0"),
        )
        result = project_closed_order_to_observed_economics(closed_order=order)
        assert result.symbol == "ethusdt"
        assert result.side == "sell"
        assert result.order_type == "limit"
        assert result.quantity == Decimal("0.137")
        assert result.price == Decimal("1234.567")
        assert result.reduce_only is True

    def test_symbol_with_padding_preserved_literal(self):
        # Auditoría adversarial 3.91 (N29b): "ethusdt" no discrimina un
        # strip() indebido -- este fixture sí tiene espacios.
        order = _closed_order(symbol=" BTCUSDT ")
        assert project_closed_order_to_observed_economics(closed_order=order).symbol == " BTCUSDT "

    def test_market_price_projects_to_none(self):
        order = _closed_order(order_type="market", price=None)
        assert project_closed_order_to_observed_economics(closed_order=order).price is None

    def test_rejects_wrong_type(self):
        with pytest.raises(TypeError):
            project_closed_order_to_observed_economics(closed_order=_open_order())

    def test_rejects_non_bybit_type(self):
        with pytest.raises(TypeError):
            project_closed_order_to_observed_economics(closed_order=object())

    @pytest.mark.parametrize("kw", [
        # filled: filled_quantity == quantity
        dict(remote_status="filled", filled_quantity=Decimal("1"), filled_value=Decimal("100"),
             average_price=Decimal("99.5"), cancel_type=None, reject_reason=None),
        # cancelled: filled_quantity < quantity, con y sin ejecución parcial
        dict(remote_status="cancelled", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
             average_price=None, cancel_type="CancelByUser", reject_reason=None),
        dict(remote_status="cancelled", filled_quantity=Decimal("0.5"), filled_value=Decimal("50"),
             average_price=Decimal("100"), cancel_type="CancelByUser", reject_reason=None),
        # rejected: sin ejecución alguna
        dict(remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
             average_price=None, cancel_type=None, reject_reason="EC_InsufficientBalance"),
    ])
    def test_no_branching_by_remote_status(self, kw):
        # Mismos siete campos económicos, distinto estado terminal (y
        # distinta evolución/ejecución) -> proyección idéntica (ADR-014
        # D3/D4/D8: el estado terminal no altera la economía original).
        baseline = project_closed_order_to_observed_economics(closed_order=_closed_order())
        varied = project_closed_order_to_observed_economics(
            closed_order=_closed_order(**kw)
        )
        assert baseline == varied

    @pytest.mark.parametrize("overrides", [
        dict(exchange_order_id="SOME-OTHER-EXCHANGE-ID"),
        dict(server_time_ms=1),
        dict(remote_created_time_ms=1, remote_updated_time_ms=1),
        dict(average_price=Decimal("77")),
    ])
    def test_metadata_variation_does_not_affect_projection(self, overrides):
        baseline = project_closed_order_to_observed_economics(closed_order=_closed_order())
        varied = project_closed_order_to_observed_economics(
            closed_order=_closed_order(**overrides)
        )
        assert baseline == varied


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
        imports = self._module_imports(_projections_module)
        assert set(imports) == {
            "execution_gateway.observed_order_economics_contracts",
            "execution_gateway.order_history_lookup_contracts",
            "execution_gateway.order_realtime_lookup_contracts",
        }

    def test_no_clock_or_environment_access(self):
        src = inspect.getsource(_projections_module)
        for banned in ("time.time", "datetime.now", "os.environ", "open(", "socket.", "random."):
            assert banned not in src
