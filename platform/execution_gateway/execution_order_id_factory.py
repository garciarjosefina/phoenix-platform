import uuid

from execution_gateway.execution_identity_contracts import ExecutionOrderId

_EXECUTION_ORDER_ID_PREFIX = "ord_"


def create_execution_order_id() -> ExecutionOrderId:
    """Generador EXPLÍCITO y autorizado de identidades de orden Phoenix.

    Vive separado del contrato a propósito: `ExecutionOrderId` recibe una
    identidad, nunca la fabrica en `__post_init__` ni por `default_factory`
    (a diferencia del patrón de `phoenix_core`, congelado, que sí
    autogenera). Un contrato que se autogenera identidad no puede
    representar una identidad ya existente -- p.ej. una leída de vuelta
    desde el exchange.

    Produce "ord_" + `uuid4().hex`: 4 + 32 = 36 caracteres, el máximo que
    admite `orderLinkId` de Bybit (ADR-008). Conserva íntegros los 122
    bits aleatorios efectivos de UUID4 -- no se trunca, no se recorta, no
    se elimina ningún carácter del hex.

    Sobre colisiones: UUID4 ofrece una garantía PROBABILÍSTICA, no una
    imposibilidad matemática. Phoenix no mantiene ningún registro global
    de identidades emitidas, así que la unicidad descansa enteramente en
    esos 122 bits. Bybit exige que `orderLinkId` sea único; una colisión
    sería rechazada por el exchange, no detectada localmente.

    Deliberadamente NO deriva de `phoenix_core.ids.order_id()` (42
    caracteres -- incompatible con la frontera) ni lo adapta de ninguna
    forma: son identidades de bounded contexts distintos.
    """
    return ExecutionOrderId(value=_EXECUTION_ORDER_ID_PREFIX + uuid.uuid4().hex)
