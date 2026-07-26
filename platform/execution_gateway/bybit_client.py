from abc import ABCMeta

from execution_gateway.bybit_create_order_operation import BybitCreateOrderOperation
from execution_gateway.bybit_create_order_request import BybitCreateOrderRequest
from execution_gateway.bybit_response import BybitResponse


class BybitDemoClient(metaclass=ABCMeta):
    @classmethod
    def __subclasshook__(cls, C):
        if cls is BybitDemoClient:
            if any("place_order" in B.__dict__ for B in C.__mro__):
                return True
            return False
        return NotImplemented

    def __init__(self, create_order_operation: BybitCreateOrderOperation) -> None:
        if not isinstance(create_order_operation, BybitCreateOrderOperation):
            raise TypeError(
                f"create_order_operation must be BybitCreateOrderOperation, "
                f"got: {type(create_order_operation).__name__}"
            )
        self._create_order_operation = create_order_operation

    def create_order(self, *, request: BybitCreateOrderRequest) -> BybitResponse:
        if not isinstance(request, BybitCreateOrderRequest):
            raise TypeError(
                f"request must be BybitCreateOrderRequest, "
                f"got: {type(request).__name__}"
            )
        return self._create_order_operation.execute(request=request)
