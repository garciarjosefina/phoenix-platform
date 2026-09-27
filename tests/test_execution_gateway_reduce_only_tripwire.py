"""Hito 3.92 (ADR-014 G3): tripwire causal que garantiza que el adapter de
ejecución sigue enviando `reduce_only=False` -- exactamente la semántica
local que el Economic Comparator ACEPTADO de Hito 3.91 asume
(`economic_comparator._ATTEMPTED_REDUCE_ONLY`). El comparador NO se toca
en este hito: el tripwire vive alrededor de la semántica ya existente."""
import execution_gateway.economic_comparator as _comparator_module
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.contracts import ExecutionRequest

import pytest


def _make_request(order_id="ord_tripwire", **overrides):
    kwargs = dict(
        order_id=order_id, symbol="BTCUSDT", side="buy", order_type="market", quantity=0.001,
    )
    kwargs.update(overrides)
    return ExecutionRequest(**kwargs)


class _CapturingClient:
    def __init__(self):
        self.received_requests: list[BybitCreateOrderRequest] = []

    def place_order(self, request: BybitCreateOrderRequest) -> BybitCreateOrderResult:
        self.received_requests.append(request)
        return BybitCreateOrderResult(order_id="bybit-1", order_link_id=request.order_link_id)


def _execute_and_capture(**overrides):
    client = _CapturingClient()
    gw = BybitExecutionGateway(client=client)
    gw.execute(_make_request(**overrides))
    return client.received_requests[0]


class TestComparatorAssumptionIsFrozenAndFalse:
    """Ancla explícita de la premisa que 3.92 hereda de 3.91 -- si esta
    constante deja de ser exactamente `False`, la propia batería de
    mutación aceptada de Hito 3.91 ya debe fallar; este test documenta la
    premisa, no la re-decide."""

    def test_comparator_local_reduce_only_assumption_is_literally_false(self):
        assert _comparator_module._ATTEMPTED_REDUCE_ONLY is False


class TestAdapterReduceOnlyMatchesComparatorAssumption:
    """Tripwire conductual (R1/R4): atraviesa el camino público real
    (`ExecutionRequest` -> `execute()` -> `BybitCreateOrderRequest`) para
    al menos dos valores de `side` y de `order_type` -- si el adapter
    derivara `reduce_only` de algún dato no autorizado (p.ej. `side`), una
    fixture de un solo lado no lo detectaría."""

    @pytest.mark.parametrize(
        "overrides",
        [
            dict(side="buy", order_type="market", quantity=0.001),
            dict(side="sell", order_type="market", quantity=0.001),
            dict(side="buy", order_type="limit", quantity=1.0, price=100.0),
            dict(side="sell", order_type="limit", quantity=1.0, price=100.0),
        ],
        ids=["buy-market", "sell-market", "buy-limit", "sell-limit"],
    )
    def test_reduce_only_equals_comparator_assumption_across_sides_and_types(self, overrides):
        received = _execute_and_capture(**overrides)
        # R3: identidad estricta (`is`), no una comprobación de truthiness
        # -- `BybitCreateOrderRequest.__post_init__` ya exige `bool`
        # estricto, así que `is False`/`is True` es la comparación correcta
        # y no deja pasar un valor "falsy" distinto por coincidencia.
        assert received.reduce_only is _comparator_module._ATTEMPTED_REDUCE_ONLY

    def test_reduce_only_is_exactly_false_not_merely_falsy(self):
        received = _execute_and_capture()
        assert received.reduce_only is False
