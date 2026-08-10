from execution_gateway.bybit_endpoint import BybitEndpoint

BYBIT_CREATE_ORDER_ENDPOINT = BybitEndpoint(
    method="POST",
    path="/v5/order/create",
)

BYBIT_POSITIONS_ENDPOINT = BybitEndpoint(
    method="GET",
    path="/v5/position/list",
)

__all__ = ["BYBIT_CREATE_ORDER_ENDPOINT", "BYBIT_POSITIONS_ENDPOINT"]
