from execution_gateway.config import GatewayConfig
from execution_gateway.gateway import ExecutionGateway
from execution_gateway.dry_run_gateway import DryRunExecutionGateway


def create_execution_gateway(config: GatewayConfig) -> ExecutionGateway:
    if config.dry_run:
        return DryRunExecutionGateway(config)
    raise NotImplementedError(
        "Live execution is not yet implemented. Use GatewayConfig(dry_run=True)."
    )
