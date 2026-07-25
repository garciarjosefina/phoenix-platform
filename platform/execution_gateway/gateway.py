from typing import Protocol, runtime_checkable

from execution_gateway.contracts import ExecutionRequest, ExecutionResult


@runtime_checkable
class ExecutionGateway(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...
