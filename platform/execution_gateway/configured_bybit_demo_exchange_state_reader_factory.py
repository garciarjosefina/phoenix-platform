from execution_gateway.bybit_demo_execution_config import BybitDemoExecutionConfig
from execution_gateway.bybit_demo_exchange_state_reader_factory import (
    create_bybit_demo_exchange_state_reader,
)
from execution_gateway.composite_exchange_state_reader import CompositeExchangeStateReader
from execution_gateway.configured_bybit_demo_open_orders_reader_factory import (
    create_configured_bybit_demo_open_orders_reader,
)
from execution_gateway.configured_bybit_demo_positions_reader_factory import (
    create_configured_bybit_demo_positions_reader,
)
from execution_gateway.configured_bybit_demo_wallet_balance_reader_factory import (
    create_configured_bybit_demo_wallet_balance_reader,
)


def create_configured_bybit_demo_exchange_state_reader(
    *,
    config: BybitDemoExecutionConfig,
) -> CompositeExchangeStateReader:
    if not isinstance(config, BybitDemoExecutionConfig):
        raise TypeError(
            f"config must be BybitDemoExecutionConfig, got: {type(config).__name__}"
        )
    # Reutiliza sin modificar las tres factories configuradas ya aceptadas
    # (Hitos 3.70/3.71/3.72) -- cada una construye su propio grafo GET
    # completo e independiente a partir del mismo config (mismas
    # credenciales, mismo recv_window, mismo timeout). No se comparte una
    # única instancia de transporte/sender/api entre las tres: cada Port
    # ya es exactly-once e independiente por diseño, y compartir instancias
    # de I/O entre ellas sería una optimización no pedida ni justificada
    # para este hito (deuda documentada, no bloqueante).
    positions_reader = create_configured_bybit_demo_positions_reader(config=config)
    open_orders_reader = create_configured_bybit_demo_open_orders_reader(config=config)
    wallet_balance_reader = create_configured_bybit_demo_wallet_balance_reader(config=config)
    return create_bybit_demo_exchange_state_reader(
        positions_reader=positions_reader,
        open_orders_reader=open_orders_reader,
        wallet_balance_reader=wallet_balance_reader,
    )
