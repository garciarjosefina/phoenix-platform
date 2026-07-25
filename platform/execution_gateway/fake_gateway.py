from execution_gateway.contracts import ExecutionRequest, ExecutionResult


class FakeExecutionGateway:
    def __init__(self, result: ExecutionResult) -> None:
        self._result = result
        self._last_request: ExecutionRequest | None = None

    @property
    def last_request(self) -> ExecutionRequest | None:
        return self._last_request

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        if request.order_id != self._result.order_id:
            raise ValueError(
                f"order_id mismatch: expected {self._result.order_id!r}, got {request.order_id!r}"
            )
        self._last_request = request
        return self._result
