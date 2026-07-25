from execution_gateway.config import GatewayConfig
from execution_gateway.contracts import ExecutionRequest, ExecutionResult


class DryRunExecutionGateway:
    def __init__(self, config: GatewayConfig) -> None:
        if not config.dry_run:
            raise ValueError("DryRunExecutionGateway requires config.dry_run=True")
        self._config = config
        self._last_request: ExecutionRequest | None = None

    @property
    def last_request(self) -> ExecutionRequest | None:
        return self._last_request

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self._last_request = request
        return ExecutionResult(
            order_id=request.order_id,
            status="accepted",
        )
