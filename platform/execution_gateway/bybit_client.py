from typing import Protocol, runtime_checkable

from execution_gateway.contracts import ExecutionRequest, ExecutionResult


@runtime_checkable
class BybitDemoClient(Protocol):
    def place_order(self, request: ExecutionRequest) -> ExecutionResult:
        ...
