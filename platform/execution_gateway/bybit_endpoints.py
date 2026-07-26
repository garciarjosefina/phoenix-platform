from execution_gateway.bybit_endpoint import BybitEndpoint

BYBIT_CREATE_ORDER_ENDPOINT = BybitEndpoint(
    method="POST",
    path="/v5/order/create",
)

__all__ = ["BYBIT_CREATE_ORDER_ENDPOINT"]
