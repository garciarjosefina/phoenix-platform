from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import (
    BybitOrderHistoryLookupResult,
    BybitOrderHistoryOrderFound,
    BybitOrderHistoryOrderNotFound,
)

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


def _found(**overrides):
    defaults = dict(
        execution_order_id=_OID,
        exchange_order_id="bybit-1",
        symbol="BTCUSDT",
        side="buy",
        order_type="market",
        quantity=Decimal("0.5"),
        filled_quantity=Decimal("0.5"),
        filled_value=Decimal("30000"),
        remote_status="filled",
        reduce_only=False,
        server_time_ms=1_700_000_000_500,
        remote_created_time_ms=1_700_000_000_000,
        remote_updated_time_ms=1_700_000_000_400,
        average_price=Decimal("60000"),
    )
    defaults.update(overrides)
    return BybitOrderHistoryOrderFound(**defaults)


class TestImport:
    def test_importable_from_package(self):
        for name in (
            "BybitOrderHistoryLookupResult",
            "BybitOrderHistoryOrderFound",
            "BybitOrderHistoryOrderNotFound",
        ):
            assert hasattr(execution_gateway, name)
            assert name in execution_gateway.__all__


class TestMarker:
    def test_found_is_a_lookup_result(self):
        assert isinstance(_found(), BybitOrderHistoryLookupResult)

    def test_not_found_is_a_lookup_result(self):
        assert isinstance(BybitOrderHistoryOrderNotFound(), BybitOrderHistoryLookupResult)

    def test_found_is_not_not_found(self):
        assert not isinstance(_found(), BybitOrderHistoryOrderNotFound)

    def test_not_found_is_not_found(self):
        assert not isinstance(BybitOrderHistoryOrderNotFound(), BybitOrderHistoryOrderFound)


class TestFoundIdentity:
    def test_execution_order_id_must_be_execution_order_id(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            _found(execution_order_id="ord_" + "a" * 32)

    def test_execution_order_id_rejects_none(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            _found(execution_order_id=None)

    def test_execution_order_id_preserved_by_identity(self):
        marker = ExecutionOrderId(value="ord_" + "b" * 32)
        assert _found(execution_order_id=marker).execution_order_id is marker

    def test_exchange_order_id_must_not_be_empty(self):
        with pytest.raises(ValueError, match="exchange_order_id"):
            _found(exchange_order_id="")

    def test_exchange_order_id_must_be_str(self):
        with pytest.raises(TypeError, match="exchange_order_id"):
            _found(exchange_order_id=123)


class TestFoundFieldTypes:
    def test_side_must_be_buy_or_sell(self):
        with pytest.raises(ValueError, match="side"):
            _found(side="long")

    def test_order_type_must_be_market_or_limit(self):
        with pytest.raises(ValueError, match="order_type"):
            _found(order_type="stop")

    def test_reduce_only_must_be_bool(self):
        with pytest.raises(TypeError, match="reduce_only"):
            _found(reduce_only=1)

    def test_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="quantity"):
            _found(quantity=0.5)

    def test_quantity_must_be_positive(self):
        with pytest.raises(ValueError, match="quantity"):
            _found(quantity=Decimal("0"))

    def test_filled_quantity_must_be_decimal(self):
        with pytest.raises(TypeError, match="filled_quantity"):
            _found(filled_quantity=0.5)

    def test_filled_value_must_not_be_negative(self):
        with pytest.raises(ValueError, match="filled_value"):
            _found(filled_value=Decimal("-1"))

    def test_server_time_ms_rejects_bool(self):
        with pytest.raises(TypeError, match="server_time_ms"):
            _found(server_time_ms=True)

    def test_server_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="server_time_ms"):
            _found(server_time_ms=-1)


class TestRemoteStatus:
    def test_rejects_open_status(self):
        with pytest.raises(ValueError, match="remote_status"):
            _found(remote_status="new")

    def test_rejects_impossible_closed_status_deactivated(self):
        with pytest.raises(ValueError, match="remote_status"):
            _found(remote_status="deactivated")

    def test_rejects_impossible_closed_status_partially_filled_cancelled(self):
        with pytest.raises(ValueError, match="remote_status"):
            _found(remote_status="partially_filled_cancelled")

    def test_accepts_filled(self):
        assert _found(remote_status="filled").remote_status == "filled"

    def test_accepts_cancelled(self):
        obj = _found(
            remote_status="cancelled", filled_quantity=Decimal("0.2"), filled_value=Decimal("12000"),
            average_price=Decimal("60000"), cancel_type="CancelByUser",
        )
        assert obj.remote_status == "cancelled"

    def test_accepts_rejected(self):
        obj = _found(
            remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
            average_price=None,
        )
        assert obj.remote_status == "rejected"


class TestCrossFieldInvariants:
    """ADR-012 D3: el estado remoto debe ser congruente con la magnitud
    efectivamente ejecutada -- nunca una combinación imposible."""

    def test_filled_requires_full_fill(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _found(remote_status="filled", filled_quantity=Decimal("0.3"), quantity=Decimal("0.5"))

    def test_rejected_requires_zero_fill(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _found(
                remote_status="rejected", filled_quantity=Decimal("0.1"), quantity=Decimal("0.5"),
                average_price=Decimal("1"),
            )

    def test_cancelled_requires_partial_fill_strictly_below_quantity(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _found(
                remote_status="cancelled", filled_quantity=Decimal("0.5"), quantity=Decimal("0.5"),
                average_price=Decimal("1"), cancel_type="CancelByUser",
            )

    def test_average_price_none_requires_zero_fill(self):
        with pytest.raises(ValueError, match="average_price"):
            _found(average_price=None)  # filled_quantity=0.5 in defaults

    def test_average_price_present_requires_nonzero_fill(self):
        with pytest.raises(ValueError, match="average_price"):
            _found(
                remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
                average_price=Decimal("1"),
            )

    def test_average_price_must_be_positive_when_present(self):
        with pytest.raises(ValueError, match="average_price"):
            _found(average_price=Decimal("0"))

    def test_filled_value_zero_iff_filled_quantity_zero_direction_a(self):
        with pytest.raises(ValueError, match="filled_value"):
            _found(filled_value=Decimal("0"))  # filled_quantity=0.5 by default

    def test_filled_value_zero_iff_filled_quantity_zero_direction_b(self):
        with pytest.raises(ValueError, match="filled_value"):
            _found(
                remote_status="rejected", filled_quantity=Decimal("0"), filled_value=Decimal("5"),
                average_price=None,
            )

    def test_filled_quantity_cannot_exceed_quantity(self):
        with pytest.raises(ValueError, match="filled_quantity"):
            _found(quantity=Decimal("0.3"))  # filled_quantity=0.5 by default > quantity


class TestOrderTypePriceCoupling:
    """Idéntico al acoplamiento de OrderObservedOpen (ADR-010/3.83)."""

    def test_limit_requires_price(self):
        with pytest.raises(ValueError, match="price"):
            _found(order_type="limit", price=None)

    def test_market_forbids_price(self):
        with pytest.raises(ValueError, match="price"):
            _found(order_type="market", price=Decimal("60000"))

    def test_limit_with_price_is_valid(self):
        obj = _found(order_type="limit", price=Decimal("60000"))
        assert obj.price == Decimal("60000")


class TestCancelType:
    def test_cancel_type_must_be_none_unless_cancelled(self):
        with pytest.raises(ValueError, match="cancel_type"):
            _found(remote_status="filled", cancel_type="CancelByUser")

    def test_cancel_type_allowed_when_cancelled(self):
        obj = _found(
            remote_status="cancelled", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
            average_price=None, cancel_type="CancelByUser",
        )
        assert obj.cancel_type == "CancelByUser"

    def test_cancel_type_rejects_empty_string(self):
        with pytest.raises(ValueError, match="cancel_type"):
            _found(
                remote_status="cancelled", filled_quantity=Decimal("0"), filled_value=Decimal("0"),
                average_price=None, cancel_type="",
            )


class TestTimestamps:
    def test_updated_must_not_precede_created(self):
        with pytest.raises(ValueError, match="remote_updated_time_ms"):
            _found(remote_created_time_ms=100, remote_updated_time_ms=50)

    def test_remote_created_time_ms_rejects_negative(self):
        with pytest.raises(ValueError, match="remote_created_time_ms"):
            _found(remote_created_time_ms=-1, remote_updated_time_ms=0)

    def test_equal_created_and_updated_is_valid(self):
        obj = _found(remote_created_time_ms=100, remote_updated_time_ms=100)
        assert obj.remote_created_time_ms == obj.remote_updated_time_ms == 100


class TestNotFoundSemantics:
    def test_not_found_carries_no_fields(self):
        assert vars(BybitOrderHistoryOrderNotFound()) == {}

    def test_two_not_found_instances_are_equal(self):
        assert BybitOrderHistoryOrderNotFound() == BybitOrderHistoryOrderNotFound()

    def test_docstring_documents_semantic_boundary(self):
        doc = BybitOrderHistoryOrderNotFound.__doc__
        assert "nunca recibió" in doc
        assert "rechazada" in doc
        assert "reenviar" in doc
