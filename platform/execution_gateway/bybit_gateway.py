from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.contracts import ExecutionRequest, ExecutionResult


class BybitExecutionGateway:
    def __init__(self, client: BybitDemoClient) -> None:
        if not isinstance(client, BybitDemoClient):
            raise TypeError(
                f"client must be compatible with BybitDemoClient, got: {type(client).__name__}"
            )
        self._client = client

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        return self._client.place_order(request)
