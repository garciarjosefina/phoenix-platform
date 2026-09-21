from decimal import Decimal

import pytest

import execution_gateway
from execution_gateway.bybit_api_error import BybitApiError
from execution_gateway.bybit_order_realtime_response_interpreter import (
    BybitOrderRealtimeResponseInterpreter,
)
from execution_gateway.bybit_response import BybitResponse
from execution_gateway.bybit_response_processing_error import BybitResponseProcessingError
from execution_gateway.execution_identity_contracts import ExecutionOrderId
from execution_gateway.order_history_lookup_contracts import BybitOrderHistoryOrderFound
from execution_gateway.order_realtime_lookup_contracts import (
    BybitRealtimeOrderFoundOpen,
    BybitRealtimeOrderNotFound,
)

_OID = ExecutionOrderId(value="ord_" + "a" * 32)


def _item(**overrides):
    defaults = dict(
        orderId="bybit-order-1",
        orderLinkId=_OID.value,
        symbol="BTCUSDT",
        side="Buy",
        orderType="Limit",
        qty="1",
        price="60000",
        cumExecQty="0",
        cumExecValue="0",
        avgPrice="",
        orderStatus="New",
        cancelType="UNKNOWN",
        rejectReason="EC_NoError",
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
    return BybitOrderRealtimeResponseInterpreter().interpret(
        response=_response(**kwargs), execution_order_id=execution_order_id
    )


class TestImport:
    def test_importable_from_package(self):
        assert hasattr(execution_gateway, "BybitOrderRealtimeResponseInterpreter")
        assert "BybitOrderRealtimeResponseInterpreter" in execution_gateway.__all__


class TestInputValidation:
    def test_response_must_be_bybit_response(self):
        with pytest.raises(TypeError, match="response must be BybitResponse"):
            BybitOrderRealtimeResponseInterpreter().interpret(response={"retCode": 0}, execution_order_id=_OID)

    def test_execution_order_id_must_be_correct_type(self):
        with pytest.raises(TypeError, match="ExecutionOrderId"):
            BybitOrderRealtimeResponseInterpreter().interpret(
                response=_response(), execution_order_id="ord_" + "a" * 32
            )


class TestApiError:
    def test_nonzero_ret_code_raises_bybit_api_error(self):
        with pytest.raises(BybitApiError) as exc_info:
            _interpret(ret_code=10003, ret_msg="API key is invalid", items=[])
        assert exc_info.value.ret_code == 10003


class TestNotFound:
    def test_empty_list_returns_not_found(self):
        assert isinstance(_interpret(items=[]), BybitRealtimeOrderNotFound)

    def test_not_found_never_raises(self):
        _interpret(items=[])  # no pytest.raises


class TestOpenBranch_NewLimit:
    """Acceptance case principal del Hito 3.88 (§12): LIMIT X, qty=1,
    cumExecQty=0, orderStatus=New -> FOUND_OPEN. Desbloquea la resolución
    de identidad por realtime de ADR-013."""

    def test_new_limit_returns_found_open(self):
        result = _interpret()
        assert isinstance(result, BybitRealtimeOrderFoundOpen)

    def test_new_limit_fields(self):
        result = _interpret()
        assert result.remote_status == "new"
        assert result.filled_quantity == Decimal("0")
        assert result.average_price is None
        assert result.price == Decimal("60000")
        assert result.reduce_only is False
        assert result.execution_order_id is _OID

    def test_server_time_ms_from_response_envelope(self):
        result = _interpret(time_ms=1_234_567)
        assert result.server_time_ms == 1_234_567

    def test_created_and_updated_time_separated(self):
        result = _interpret(items=[_item(createdTime="100", updatedTime="400")])
        assert result.remote_created_time_ms == 100
        assert result.remote_updated_time_ms == 400
        assert result.server_time_ms != result.remote_created_time_ms


class TestOpenBranch_PartiallyFilled:
    def test_partially_filled_returns_found_open(self):
        item = _item(
            cumExecQty="0.4", cumExecValue="24000", avgPrice="60000", orderStatus="PartiallyFilled",
        )
        result = _interpret(items=[item])
        assert isinstance(result, BybitRealtimeOrderFoundOpen)
        assert result.remote_status == "partially_filled"

    def test_partial_quantities_preserved(self):
        item = _item(
            qty="1", cumExecQty="0.4", cumExecValue="24000", avgPrice="60000",
            orderStatus="PartiallyFilled",
        )
        result = _interpret(items=[item])
        assert result.quantity == Decimal("1")
        assert result.filled_quantity == Decimal("0.4")
        assert result.filled_value == Decimal("24000")
        assert result.average_price == Decimal("60000")

    def test_not_converted_to_fill_ledger(self):
        # Sólo agregados a nivel de orden -- ningún campo de fills
        # individuales existe en el contrato (mismo principio que 3.86).
        import dataclasses
        fields = {f.name for f in dataclasses.fields(BybitRealtimeOrderFoundOpen)}
        assert "fills" not in fields
        assert "executions" not in fields


class TestClosedRowReturnedByRealtime:
    """Hito 3.88 §7: documentación oficial confirma que `openOnly` se
    ignora al filtrar por orderLinkId -- una fila CERRADA es una respuesta
    legítima y esperada, no un error. Debe representarse con el MISMO
    contrato de 3.86 (BybitOrderHistoryOrderFound), nunca colapsada en
    NOT_FOUND ni forzada en FOUND_OPEN."""

    def test_filled_returns_history_found_type(self):
        item = _item(
            orderType="Market", price="", qty="1", cumExecQty="1", cumExecValue="60000",
            avgPrice="60000", orderStatus="Filled",
        )
        result = _interpret(items=[item])
        assert isinstance(result, BybitOrderHistoryOrderFound)
        assert not isinstance(result, BybitRealtimeOrderFoundOpen)

    def test_filled_fields_correct(self):
        item = _item(
            orderType="Market", price="", qty="1", cumExecQty="1", cumExecValue="60000",
            avgPrice="60000", orderStatus="Filled",
        )
        result = _interpret(items=[item])
        assert result.remote_status == "filled"
        assert result.filled_quantity == result.quantity == Decimal("1")
        assert result.cancel_type is None

    def test_cancelled_zero_fill_returns_history_found_type(self):
        item = _item(cumExecQty="0", cumExecValue="0", avgPrice="0", orderStatus="Cancelled")
        result = _interpret(items=[item])
        assert isinstance(result, BybitOrderHistoryOrderFound)
        assert result.remote_status == "cancelled"

    def test_cancelled_never_becomes_not_found(self):
        item = _item(cumExecQty="0", cumExecValue="0", avgPrice="0", orderStatus="Cancelled")
        result = _interpret(items=[item])
        assert not isinstance(result, BybitRealtimeOrderNotFound)

    def test_rejected_returns_history_found_type(self):
        item = _item(cumExecQty="0", cumExecValue="0", avgPrice="0", orderStatus="Rejected")
        result = _interpret(items=[item])
        assert isinstance(result, BybitOrderHistoryOrderFound)
        assert result.remote_status == "rejected"

    def test_closed_row_preserves_cancel_type_normalization(self):
        item = _item(
            cumExecQty="0", cumExecValue="0", avgPrice="0", orderStatus="Cancelled",
            cancelType="CancelByUser",
        )
        result = _interpret(items=[item])
        assert result.cancel_type == "CancelByUser"


class TestUnsupportedStatus:
    """Untriggered/Triggered: condicionales, estructuralmente imposibles
    para una orden correlacionada por ExecutionOrderId (Phoenix nunca crea
    condicionales). Deactivated/PartiallyFilledCanceled: imposibles por
    ADR-012 F2. Opción B: fail-closed, sin ampliar taxonomía."""

    @pytest.mark.parametrize("status", [
        "Untriggered", "Triggered", "Deactivated", "PartiallyFilledCanceled",
        "SomeUnknownFutureStatus", "",
    ])
    def test_rejects_unsupported_status(self, status):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderStatus=status)])


class TestCardinality:
    def test_zero_results_is_not_found(self):
        assert isinstance(_interpret(items=[]), BybitRealtimeOrderNotFound)

    def test_two_correlated_results_fail_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(), _item(orderId="bybit-order-2")])

    def test_does_not_pick_first_of_duplicates(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(orderId="A"), _item(orderId="B"), _item(orderId="C")])

    def test_one_open_and_one_closed_duplicate_fails_closed(self):
        # Caso adversarial propio de esta primitiva: si Bybit devolviera
        # simultáneamente una fila abierta y una cerrada para el mismo X
        # (cardinalidad ambigua), nunca se elige ninguna.
        open_row = _item()
        closed_row = _item(orderId="bybit-2", cumExecQty="1", cumExecValue="60000", avgPrice="60000", orderStatus="Filled")
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[open_row, closed_row])


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

    def test_exchange_order_id_matching_requested_identity_never_substitutes(self):
        item = _item(orderId=_OID.value, orderLinkId="ord_" + "b" * 32)
        with pytest.raises(BybitResponseProcessingError):
            _interpret(execution_order_id=_OID, items=[item])


class TestPagination:
    def test_nonempty_cursor_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(result_override={"category": "linear", "list": [_item()], "nextPageCursor": "abc"})

    def test_empty_cursor_is_fine(self):
        result = _interpret(result_override={"category": "linear", "list": [_item()], "nextPageCursor": ""})
        assert isinstance(result, BybitRealtimeOrderFoundOpen)

    def test_missing_cursor_key_is_fine(self):
        result = _interpret(result_override={"category": "linear", "list": [_item()]})
        assert isinstance(result, BybitRealtimeOrderFoundOpen)


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

    def test_reduce_only_wrong_type_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(reduceOnly="false")])

    def test_invalid_decimal_qty_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="not-a-number")])

    def test_nan_decimal_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(cumExecQty="NaN")])

    def test_infinity_decimal_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty="Infinity")])

    def test_non_string_decimal_field_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(qty=0.5)])

    def test_invalid_timestamp_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(createdTime="not-a-timestamp")])

    def test_negative_timestamp_fails_closed(self):
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(createdTime="-1")])


class TestSentinels:
    """Lecciones aplicadas de 3.86 (post-corrección) -- confirmadas contra
    el ejemplo oficial de /v5/order/realtime (orden New: avgPrice="0",
    cancelType="UNKNOWN", rejectReason="EC_NoError")."""

    def test_avg_price_empty_is_none(self):
        result = _interpret(items=[_item(avgPrice="")])
        assert result.average_price is None

    def test_avg_price_zero_is_none(self):
        result = _interpret(items=[_item(avgPrice="0")])
        assert result.average_price is None

    def test_price_zero_is_none_market_precedent(self):
        result = _interpret(items=[_item(orderType="Market", price="0")])
        assert result.price is None

    def test_reject_reason_ec_no_error_is_none(self):
        result = _interpret(items=[_item(rejectReason="EC_NoError")])
        assert result.reject_reason is None

    def test_reject_reason_missing_is_none(self):
        result = _interpret(items=[_item(rejectReason=None)])
        assert result.reject_reason is None

    def test_cancel_type_unknown_normalized_to_none_on_open_order(self):
        result = _interpret(items=[_item(cancelType="UNKNOWN")])
        assert isinstance(result, BybitRealtimeOrderFoundOpen)

    def test_cancel_type_real_reason_on_open_order_fails_closed(self):
        # Una orden ABIERTA nunca fue cancelada -- un motivo real aquí es
        # una respuesta inconsistente.
        with pytest.raises(BybitResponseProcessingError):
            _interpret(items=[_item(cancelType="CancelByUser")])


class TestOfficialResponseExample:
    """Fixture derivado literalmente del ejemplo de respuesta oficial de
    GET /v5/order/realtime (docs/v5/order/open-order)."""

    def test_official_new_limit_example(self):
        item = _item(
            orderId="fd4300ae-7847-404e-b947-b46980a4d140",
            symbol="ETHUSDT", price="1600.00", qty="0.10", side="Buy",
            orderStatus="New", cancelType="UNKNOWN", rejectReason="EC_NoError",
            avgPrice="0", cumExecQty="0.00", cumExecValue="0", orderType="Limit",
            reduceOnly=False, createdTime="1684738540559", updatedTime="1684738540561",
        )
        result = _interpret(items=[item])
        assert isinstance(result, BybitRealtimeOrderFoundOpen)
        assert result.remote_status == "new"
        assert result.average_price is None
        assert result.price == Decimal("1600.00")
        assert result.remote_created_time_ms == 1684738540559
        assert result.remote_updated_time_ms == 1684738540561


class TestMarketNegativeSemantics:
    """§13: un MARKET puede llenarse antes de que realtime lo vea abierto
    -- NOT_FOUND aquí no concluye nada sobre X."""

    def test_not_found_does_not_imply_never_existed(self):
        result = _interpret(items=[])
        assert isinstance(result, BybitRealtimeOrderNotFound)
        doc = BybitRealtimeOrderNotFound.__doc__
        assert "nunca existió" in doc
