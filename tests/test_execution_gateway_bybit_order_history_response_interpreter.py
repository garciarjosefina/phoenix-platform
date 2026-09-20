from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_order_history_response_interpreter import BybitOrderHistoryResponseInterpreter
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import (
    BybitOrderHistoryOrderFound,
    BybitOrderHistoryOrderNotFound,
)

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


def _item(**overrides):
    defaults = dict(
        orderId="bybit-order-1",
        orderLinkId=_OID.value,
        symbol="BTCUSDT",
        side="Buy",
        orderType="Market",
        qty="0.5",
        cumExecQty="0.5",
        cumExecValue="30000",
        avgPrice="60000",
        orderStatus="Filled",
        reduceOnly=False,
        createdTime="1700000000000",
        updatedTime="1700000000400",
    )
    defaults.update(overrides)
    return defaults


def _response(*, ret_code=0, ret_msg="OK", items=None, time_ms=1_700_000_000_500, result_override=None):
    if result_override is not None:
        result = result_override
    else:
        result = {"category": "linear", "list": list(items if items is not None else [_item()]), "nextPageCursor": ""}
    return BybitResponse(ret_code=ret_code, ret_msg=ret_msg, result=result, ret_ext_info={}, time_ms=time_ms)


def _interpret(*, execution_order_id=_OID, **kwargs):
    return BybitOrderHistoryResponseInterpreter().interpret(
        response=_response(**kwargs), execution_order_id=execution_order_id
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitOrderHistoryResponseInterpreter")
        assert "BybitOrderHistoryResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitOrderHistoryResponseInterpreter().interpret(response={"retCode": 0}, execution_order_id=_OID)

    def test_execution_order_id_must_be_correct_type(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            BybitOrderHistoryResponseInterpreter().interpret(
                response=_response(), execution_order_id="ord_" + "a" * 32
            )


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10003, ret_msg="API key is invalid", items=[])
        assert exc_info.value.ret_code == 10003

    def test_ret_code_checked_before_touching_result(self):
        with pytest.raises(BybitApiError):
            _interpret(ret_code=10004, ret_msg="error sign", result_override="not-a-mapping")


class TestNotFound:
    def test_empty_list_returns_not_found(self):
        result = _interpret(items=[])
        assert isinstance(result, BybitOrderHistoryOrderNotFound)

    def test_not_found_is_a_return_value_never_an_exception(self):
        # No debe lanzarse ninguna excepción -- NOT_FOUND es un resultado
        # legítimo del dominio, nunca un error (Hito 3.86, §19).
        _interpret(items=[])  # no pytest.raises


class TestFound:
    def test_single_item_returns_found(self):
        result = _interpret()
        assert isinstance(result, BybitOrderHistoryOrderFound)

    def test_found_carries_requested_execution_order_id_by_identity(self):
        result = _interpret(execution_order_id=_OID)
        assert result.execution_order_id is _OID

    def test_market_filled_fields(self):
        result = _interpret()
        assert result.exchange_order_id == "bybit-order-1"
        assert result.symbol == "BTCUSDT"
        assert result.side == "buy"
        assert result.order_type == "market"
        assert result.quantity == Decimal("0.5")
        assert result.filled_quantity == Decimal("0.5")
        assert result.filled_value == Decimal("30000")
        assert result.remote_status == "filled"
        assert result.average_price == Decimal("60000")
        assert result.price is None
        assert result.reduce_only is False

    def test_server_time_ms_from_response_envelope(self):
        result = _interpret(time_ms=1_234_567)
        assert result.server_time_ms == 1_234_567

    def test_created_and_updated_time_preserved_separately(self):
        result = _interpret(items=[_item(createdTime="100", updatedTime="400")])
        assert result.remote_created_time_ms == 100
        assert result.remote_updated_time_ms == 400
        assert result.remote_created_time_ms != result.remote_updated_time_ms

    def test_server_time_ms_not_confused_with_created_or_updated(self):
        result = _interpret(items=[_item(createdTime="100", updatedTime="400")], time_ms=999)
        assert result.server_time_ms == 999
        assert result.server_time_ms not in (result.remote_created_time_ms, result.remote_updated_time_ms)


class TestCardinality:
    def test_zero_results_is_not_found_not_error(self):
        assert isinstance(_interpret(items=[]), BybitOrderHistoryOrderNotFound)

    def test_two_correlated_results_fail_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(), _item(orderId="bybit-order-2")])

    def test_does_not_pick_first_of_duplicates(self):
        # Verificado indirectamente: la única forma de "elegir el primero"
        # sería no lanzar -- comprobamos que SIEMPRE falla cerrado.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderId="A"), _item(orderId="B"), _item(orderId="C")])


class TestCorrelation:
    def test_mismatched_order_link_id_fails_closed(self):
        other = ExecutionOrderId(value="ord_" + "b" * 32)
        with pytest.raises(BybitResponseProcessingError):
            _interpret(execution_order_id=other, items=[_item(orderLinkId=_OID.value)])

    def test_empty_order_link_id_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderLinkId="")])

    def test_missing_order_link_id_fails_closed(self):
        item = _item()
        del item["orderLinkId"]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_exchange_order_id_never_used_as_fallback_identity(self):
        # orderLinkId ausente pero orderId (exchange) presente y "parecido" --
        # nunca debe usarse como sustituto de la identidad Phoenix.
        item = _item(orderLinkId="")
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])


class TestPagination:
    def test_nonempty_cursor_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [_item()], "nextPageCursor": "abc"})

    def test_empty_cursor_string_is_fine(self):
        result = _interpret(result_override={"category": "linear", "list": [_item()], "nextPageCursor": ""})
        assert isinstance(result, BybitOrderHistoryOrderFound)

    def test_missing_cursor_key_is_fine(self):
        result = _interpret(result_override={"category": "linear", "list": [_item()]})
        assert isinstance(result, BybitOrderHistoryOrderFound)


class TestMalformedResponse:
    def test_missing_list_key_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear"})

    def test_result_not_a_mapping_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override="not-a-mapping")

    def test_list_not_a_list_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": "not-a-list"})

    def test_item_not_a_mapping_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=["not-a-mapping"])

    @pytest.mark.parametrize("field", [
        "orderId", "orderLinkId", "symbol", "side", "orderType", "qty",
        "cumExecQty", "cumExecValue", "orderStatus", "reduceOnly",
        "createdTime", "updatedTime",
    ])
    def test_missing_required_field_fails_closed(self, field):
        item = _item()
        del item[field]
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])

    def test_wrong_type_side_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(side="LONG")])

    def test_wrong_type_order_type_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderType="Stop")])

    def test_reduce_only_wrong_type_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(reduceOnly="false")])

    def test_invalid_decimal_qty_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="not-a-number")])

    def test_invalid_decimal_cum_exec_qty_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(cumExecQty="NaN")])

    def test_non_string_decimal_field_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty=0.5)])

    def test_invalid_timestamp_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(createdTime="not-a-timestamp")])

    def test_non_string_timestamp_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(createdTime=1700000000000)])

    def test_negative_timestamp_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(createdTime="-1")])


class TestClosedStatusTaxonomy:
    """ADR-012 D1-D3: sólo Filled/Cancelled/Rejected son admisibles para una
    orden Phoenix (linear, market/limit). Opción B (Hito 3.86, §13): el
    interpreter falla cerrado ante cualquier otro estado."""

    def test_filled_accepted(self):
        result = _interpret(items=[_item(orderStatus="Filled")])
        assert result.remote_status == "filled"

    def test_cancelled_accepted(self):
        result = _interpret(items=[_item(
            orderStatus="Cancelled", cumExecQty="0", cumExecValue="0", avgPrice="",
        )])
        assert result.remote_status == "cancelled"

    def test_rejected_accepted(self):
        result = _interpret(items=[_item(
            orderStatus="Rejected", cumExecQty="0", cumExecValue="0", avgPrice="",
        )])
        assert result.remote_status == "rejected"

    @pytest.mark.parametrize("status", [
        "New", "PartiallyFilled", "Untriggered", "Triggered",
        "Deactivated", "PartiallyFilledCanceled",
    ])
    def test_rejects_status_outside_admissible_closed_set(self, status):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus=status)])


class TestPartialFillCancelled:
    """Caso obligatorio del Hito 3.86 (§14): LIMIT qty=1, cumExecQty=0.4,
    Cancelled -- la ejecución parcial se preserva, sin convertirse en Fill
    Ledger."""

    def test_partial_fill_preserved(self):
        item = _item(
            orderType="Limit", price="60000", qty="1", cumExecQty="0.4", cumExecValue="24000",
            avgPrice="60000", orderStatus="Cancelled",
        )
        result = _interpret(items=[item])
        assert result.quantity == Decimal("1")
        assert result.filled_quantity == Decimal("0.4")
        assert result.filled_value == Decimal("24000")
        assert result.average_price == Decimal("60000")
        assert result.remote_status == "cancelled"
        assert result.price == Decimal("60000")

    def test_cancel_type_preserved_verbatim(self):
        item = _item(
            orderType="Limit", price="60000", qty="1", cumExecQty="0.4", cumExecValue="24000",
            avgPrice="60000", orderStatus="Cancelled", cancelType="CancelByUser",
        )
        result = _interpret(items=[item])
        assert result.cancel_type == "CancelByUser"


class TestRejected:
    def test_reject_reason_preserved_verbatim(self):
        item = _item(
            orderType="Limit", price="60000", qty="1", cumExecQty="0", cumExecValue="0", avgPrice="",
            orderStatus="Rejected", rejectReason="EC_NoImmediateQtyToFill",
        )
        result = _interpret(items=[item])
        assert result.reject_reason == "EC_NoImmediateQtyToFill"
        assert result.remote_status == "rejected"

    def test_does_not_construct_order_rejected_by_exchange(self):
        # El resultado debe ser BybitOrderHistoryOrderFound -- nunca el
        # evento REMOTE del Ledger (OrderRejectedByExchange pertenece a la
        # respuesta directa de submission, no a una observación posterior).
        item = _item(
            orderType="Limit", price="60000", qty="1", cumExecQty="0", cumExecValue="0", avgPrice="",
            orderStatus="Rejected",
        )
        result = _interpret(items=[item])
        assert type(result).__name__ == "BybitOrderHistoryOrderFound"


class TestSentinels:
    def test_avg_price_empty_string_is_none_without_fill(self):
        item = _item(orderStatus="Rejected", cumExecQty="0", cumExecValue="0", avgPrice="")
        result = _interpret(items=[item])
        assert result.average_price is None

    def test_price_empty_string_is_none(self):
        item = _item(price="")
        result = _interpret(items=[item])
        assert result.price is None

    def test_price_zero_is_none_market_precedent(self):
        item = _item(price="0")
        result = _interpret(items=[item])
        assert result.price is None

    def test_reject_reason_ec_no_error_is_none(self):
        item = _item(rejectReason="EC_NoError")
        result = _interpret(items=[item])
        assert result.reject_reason is None

    def test_reject_reason_empty_is_none(self):
        item = _item(rejectReason="")
        result = _interpret(items=[item])
        assert result.reject_reason is None

    def test_reject_reason_missing_is_none(self):
        result = _interpret(items=[_item()])
        assert result.reject_reason is None

    def test_cancel_type_missing_is_none_for_filled(self):
        result = _interpret(items=[_item()])
        assert result.cancel_type is None

    def test_cancel_type_empty_is_none(self):
        result = _interpret(items=[_item(cancelType="")])
        assert result.cancel_type is None

    def test_unexpected_cancel_type_on_non_cancelled_order_fails_closed(self):
        # MENOR-1 (ADR-012): sin sentinel documentado -- cualquier valor no
        # vacío en una orden no cancelada debe fallar cerrado vía la
        # invariante del contrato, nunca descartarse en silencio.
        item = _item(orderStatus="Filled", cancelType="CancelByUser")
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[item])
