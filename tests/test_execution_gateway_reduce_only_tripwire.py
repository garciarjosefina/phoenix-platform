"""Hito 3.92 (ADR-014 G3): tripwire causal que garantiza que el adapter de
ejecución sigue enviando `reduce_only=False` -- exactamente la semántica
local que el Economic Comparator ACEPTADO de Hito 3.91 asume
(`economic_comparator._ATTEMPTED_REDUCE_ONLY`). El comparador NO se toca
en este hito: el tripwire vive alrededor de la semántica ya existente.

Corrección post-auditoría adversarial (IMPORTANTE-1): la matriz original
sólo variaba `side`/`order_type` mientras mantenía `symbol="BTCUSDT"`,
`order_id="ord_tripwire"` y `price=100.0` constantes en todos los casos no
default -- una derivación de `reduce_only` desde `symbol`, `price` o
`order_id` (p.ej. `reduce_only=(price > 1000)`) sobrevivía sin que ningún
test lo notara. La matriz de abajo varía cada dimensión de
`ExecutionRequest` de forma independiente, con al menos un valor
"sorpresivo" por dimensión, y exige en cada caso DOS garantías: (A) el
valor absoluto congelado `is False` -- no sólo relativo a otro componente
-- y (B) la alineación semántica con el comparador de 3.91."""
import execution_gateway.economic_comparator as _comparator_module
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_create_order_result import BybitCreateOrderResult
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.contracts import ExecutionRequest

import pytest

_ORD_A = "ord_" + "a" * 32


def _make_request(order_id=_ORD_A, **overrides):
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
    """Matriz discriminante: cada fixture aísla una dimensión de
    `ExecutionRequest` con un valor no-default, para que una derivación de
    `reduce_only` desde CUALQUIERA de ellas falle causalmente."""

    _MATRIX = [
        # side/order_type (cobertura preexistente, preservada)
        ("buy-market", dict(side="buy", order_type="market", symbol="BTCUSDT", quantity=0.001)),
        ("sell-market", dict(side="sell", order_type="market", symbol="BTCUSDT", quantity=0.001)),
        ("buy-limit", dict(side="buy", order_type="limit", symbol="BTCUSDT", quantity=1.0, price=100.0)),
        ("sell-limit", dict(side="sell", order_type="limit", symbol="BTCUSDT", quantity=1.0, price=100.0)),
        # symbol -- mata R4d: reduce_only=(symbol != "BTCUSDT")
        ("symbol-ethusdt", dict(side="buy", order_type="market", symbol="ETHUSDT", quantity=0.001)),
        ("symbol-solusdt", dict(side="buy", order_type="market", symbol="SOLUSDT", quantity=0.001)),
        # price -- mata R4c: reduce_only=(price is not None and price > 1000)
        ("price-low", dict(side="buy", order_type="limit", symbol="BTCUSDT", quantity=1.0, price=0.1)),
        ("price-above-1000", dict(side="buy", order_type="limit", symbol="BTCUSDT", quantity=1.0, price=1500.0)),
        # order_id sin prefijo "ord_" -- mata R4f: reduce_only=(not order_id.startswith("ord_"))
        ("order-id-no-ord-prefix", dict(
            side="buy", order_type="market", symbol="BTCUSDT", quantity=0.001, order_id="custom-order-id-1",
        )),
        # combinación de varias dimensiones no-default a la vez
        ("combined-non-default", dict(
            side="sell", order_type="limit", symbol="ETHUSDT", quantity=1.0, price=1500.0,
            order_id="custom-order-id-2",
        )),
        # quantity -- cierra la clase de error de un futuro reduce_only=(quantity > threshold)
        ("quantity-large", dict(side="buy", order_type="market", symbol="BTCUSDT", quantity=100.0)),
        ("quantity-small-price-above-1000", dict(
            side="buy", order_type="limit", symbol="BTCUSDT", quantity=0.001, price=50_000.0,
        )),
    ]

    @pytest.mark.parametrize("overrides", [m[1] for m in _MATRIX], ids=[m[0] for m in _MATRIX])
    def test_reduce_only_is_absolutely_false_for_varied_valid_requests(self, overrides):
        received = _execute_and_capture(**overrides)
        # Garantía A: valor absoluto congelado -- no relativo a ningún otro
        # componente. R3: identidad estricta (`is`), no truthiness --
        # `BybitCreateOrderRequest.__post_init__` ya exige `bool` estricto.
        assert received.reduce_only is False

    @pytest.mark.parametrize("overrides", [m[1] for m in _MATRIX], ids=[m[0] for m in _MATRIX])
    def test_reduce_only_matches_comparator_assumption_for_varied_valid_requests(self, overrides):
        received = _execute_and_capture(**overrides)
        # Garantía B: alineación semántica con el comparador aceptado de
        # 3.91 -- ninguna de las dos garantías reemplaza a la otra: si
        # ambos componentes cambiaran a `True` simultáneamente, esta
        # aserción de igualdad seguiría pasando, pero la Garantía A (arriba)
        # seguiría fallando.
        assert received.reduce_only is _comparator_module._ATTEMPTED_REDUCE_ONLY
