from execution_gateway.config import GatewayConfig
from execution_gateway.dry_run_gateway import DryRunExecutionGateway
from execution_gateway.gateway import ExecutionGateway


def create_execution_gateway(config: GatewayConfig) -> ExecutionGateway:
    if config.dry_run:
        return DryRunExecutionGateway(config)
    raise ValueError(
        "Live execution requires a dedicated composition root for the selected adapter."
    )
