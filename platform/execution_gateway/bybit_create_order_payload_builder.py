from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest

_CATEGORY = "linear"


class BybitCreateOrderPayloadBuilder:
    def build(self, *, request: BybitCreateOrderRequest) -> dict[str, object]:
        if not isinstance(request, BybitCreateOrderRequest):
            raise TypeError(
                f"request must be BybitCreateOrderRequest, got: {type(request).__name__}"
            )

        payload: dict[str, object] = {
            "category": _CATEGORY,
            "symbol": request.symbol,
            "side": request.side,
            "orderType": request.order_type,
            "qty": str(request.quantity),
        }

        if request.order_type == "Limit":
            payload["price"] = str(request.price)

        payload["timeInForce"] = request.time_in_force
        payload["reduceOnly"] = request.reduce_only
        payload["orderLinkId"] = request.order_link_id

        return payload
