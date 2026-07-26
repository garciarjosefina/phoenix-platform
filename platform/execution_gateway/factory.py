from execution_gateway.bybit_client import BybitDemoClient
from execution_gateway.bybit_gateway import BybitExecutionGateway
from execution_gateway.config import GatewayConfig
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway.gateway import ExecutionGateway


def create_execution_gateway(
    config: GatewayConfig,
    client: BybitDemoClient | None = None,
) -> ExecutionGateway:
    if config.dry_run:
        return DryRunExecutionGateway(config)
    if client is None:
        raise ValueError(
            "A BybitDemoClient must be provided when config.dry_run=False."
        )
    return BybitExecutionGateway(client)
