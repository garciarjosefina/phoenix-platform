from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import (
    BybitRealtimeOrderFoundOpen,
    BybitRealtimeOrderLookupResult,
    BybitRealtimeOrderNotFound,
)

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


def _open(**overrides):
    defaults = dict(
        execution_order_id=_OID,
        exchange_order_id="bybit-1",
        symbol="BTCUSDT",
        side="buy",
        order_type="limit",
        quantity=Decimal("1"),
        filled_quantity=Decimal("0"),
        filled_value=Decimal("0"),
        remote_status="new",
        reduce_only=False,
        server_time_ms=1_700_000_000_500,
        remote_created_time_ms=1_700_000_000_000,
        remote_updated_time_ms=1_700_000_000_400,
        price=Decimal("60000"),
    )
    defaults.update(overrides)
    return BybitRealtimeOrderFoundOpen(**defaults)


class TestImport:
    def test_importable_from_package(self):
        for name in (
            "BybitRealtimeOrderLookupResult",
            "BybitRealtimeOrderFoundOpen",
            "BybitRealtimeOrderNotFound",
        ):
            assert hasattr(execution_gateway, name)
            assert name in execution_gateway.__all__


class TestMarker:
    def test_found_open_is_a_lookup_result(self):
        assert isinstance(_open(), BybitRealtimeOrderLookupResult)

    def test_not_found_is_a_lookup_result(self):
        assert isinstance(BybitRealtimeOrderNotFound(), BybitRealtimeOrderLookupResult)

    def test_history_found_is_not_a_realtime_lookup_result(self):
        # BybitOrderHistoryOrderFound (reutilizado para la rama cerrada) NO
        # hereda del marcador de este módulo -- es un tipo aparte, unido
        # sólo por el type hint de retorno del interpreter/reader.
        closed = BybitOrderHistoryOrderFound(
            execution_order_id=_OID, exchange_order_id="x", symbol="S", side="buy",
            order_type="market", quantity=Decimal("1"), filled_quantity=Decimal("1"),
            filled_value=Decimal("1"), remote_status="filled", reduce_only=False,
            server_time_ms=1, remote_created_time_ms=1, remote_updated_time_ms=1,
            average_price=Decimal("1"),
        )
        assert not isinstance(closed, BybitRealtimeOrderLookupResult)


class TestFoundOpenIdentity:
    def test_execution_order_id_must_be_execution_order_id(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            _open(execution_order_id="ord_" + "a" * 32)

    def test_execution_order_id_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "b" * 32)
        assert _open(execution_order_id=marker).execution_order_id is marker

    def test_exchange_order_id_must_not_be_empty(self):
        with pytest.raises(ValueError, match="exchange_order_id"):
            _open(exchange_order_id="")


class TestRemoteStatus:
    def test_rejects_closed_status(self):
        with pytest.raises(ValueError, match="remote_status"):
            _open(remote_status="filled")

    def test_rejects_untriggered(self):
        with pytest.raises(ValueError, match="remote_status"):
            _open(remote_status="untriggered")

    def test_rejects_triggered(self):
        with pytest.raises(ValueError, match="remote_status"):
            _open(remote_status="triggered")

    def test_accepts_new(self):
        assert _open(remote_status="new").remote_status == "new"

    def test_accepts_partially_filled(self):
        obj = _open(
            remote_status="partially_filled", filled_quantity=Decimal("0.4"),
            filled_value=Decimal("24000"), average_price=Decimal("60000"),
        )
        assert obj.remote_status == "partially_filled"


class TestCrossFieldInvariants:
    def test_new_requires_zero_fill(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _open(remote_status="new", filled_quantity=Decimal("0.1"), average_price=Decimal("1"))

    def test_new_requires_zero_fill_isolated_from_other_invariants(self):
        # Auditoría 3.88, hallazgo D3: `test_new_requires_zero_fill` de
        # arriba dispara la invariante de `filled_value` (fill_value=0 por
        # defecto mientras filled_quantity=0.1), no la de "new" -- no
        # prueba causalmente lo que dice probar. Aquí el fill es
        # económicamente coherente en sí mismo (average_price y
        # filled_value acoplados correctamente a filled_quantity > 0), de
        # modo que TODAS las demás invariantes pasan y la ÚNICA que puede
        # dispararse es "remote_status == 'new' requires filled_quantity
        # == 0". Si se elimina esa invariante específica, este objeto se
        # construiría sin error.
        with pytest.raises(ValueError, match="remote_status == 'new' requires filled_quantity == 0"):
            _open(
                remote_status="new", quantity=Decimal("1"),
                filled_quantity=Decimal("0.1"), filled_value=Decimal("6000"),
                average_price=Decimal("60000"),
            )

    def test_partially_filled_requires_positive_fill(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _open(remote_status="partially_filled", filled_quantity=Decimal("0"))

    def test_filled_quantity_must_be_strictly_below_quantity(self):
        # Una orden "llena" no es abierta -- sería Filled (ADR-012 D3).
        with pytest.raises(ValueError, match="filled_quantity"):
            _open(
                remote_status="partially_filled", quantity=Decimal("1"),
                filled_quantity=Decimal("1"), filled_value=Decimal("60000"),
                average_price=Decimal("60000"),
            )

    def test_average_price_none_requires_zero_fill(self):
        with pytest.raises(ValueError, match="average_price"):
            _open(average_price=Decimal("60000"))  # filled_quantity=0 default

    def test_average_price_required_with_fill(self):
        with pytest.raises(ValueError, match="average_price"):
            _open(
                remote_status="partially_filled", filled_quantity=Decimal("0.3"),
                filled_value=Decimal("18000"), average_price=None,
            )

    def test_filled_value_zero_iff_filled_quantity_zero(self):
        with pytest.raises(ValueError, match="filled_value"):
            _open(
                remote_status="partially_filled", filled_quantity=Decimal("0.3"),
                filled_value=Decimal("0"), average_price=Decimal("1"),
            )


class TestOrderTypePriceCoupling:
    def test_limit_requires_price(self):
        with pytest.raises(ValueError, match="price"):
            _open(order_type="limit", price=None)

    def test_market_forbids_price(self):
        with pytest.raises(ValueError, match="price"):
            _open(order_type="market", price=Decimal("60000"))


class TestNoCancelTypeField:
    def test_found_open_has_no_cancel_type_field(self):
        # Una orden abierta nunca fue cancelada -- el campo ni existe en
        # este contrato (a diferencia de BybitOrderHistoryOrderFound).
        import dataclasses
        fields = {f.name for f in dataclasses.fields(BybitRealtimeOrderFoundOpen)}
        assert "cancel_type" not in fields


class TestTimestamps:
    def test_updated_must_not_precede_created(self):
        with pytest.raises(ValueError, match="remote_updated_time_ms"):
            _open(remote_created_time_ms=100, remote_updated_time_ms=50)


class TestNotFoundSemantics:
    def test_not_found_carries_no_fields(self):
        assert vars(BybitRealtimeOrderNotFound()) == {}

    def test_docstring_documents_semantic_boundary(self):
        doc = BybitRealtimeOrderNotFound.__doc__
        assert "nunca existió" in doc
        assert "rechazada" in doc
        assert "cerrada" in doc
        assert "reenviar" in doc
