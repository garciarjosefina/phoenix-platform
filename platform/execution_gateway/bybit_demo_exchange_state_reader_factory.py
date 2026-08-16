from execution_gateway.composite_exchange_state_reader import CompositeExchangeStateReader
from execution_gateway.open_orders_reader import OpenOrdersReader
from execution_gateway.positions_reader import PositionsReader
from execution_gateway.wallet_balance_reader import WalletBalanceReader


def create_bybit_demo_exchange_state_reader(
    *,
    positions_reader: PositionsReader,
    open_orders_reader: OpenOrdersReader,
    wallet_balance_reader: WalletBalanceReader,
) -> CompositeExchangeStateReader:
    if not isinstance(positions_reader, PositionsReader):
        raise TypeError(
            f"positions_reader must be compatible with PositionsReader, "
            f"got: {type(positions_reader).__name__}"
        )
    if not isinstance(open_orders_reader, OpenOrdersReader):
        raise TypeError(
            f"open_orders_reader must be compatible with OpenOrdersReader, "
            f"got: {type(open_orders_reader).__name__}"
        )
    if not isinstance(wallet_balance_reader, WalletBalanceReader):
        raise TypeError(
            f"wallet_balance_reader must be compatible with WalletBalanceReader, "
            f"got: {type(wallet_balance_reader).__name__}"
        )
    return CompositeExchangeStateReader(
        positions_reader=positions_reader,
        open_orders_reader=open_orders_reader,
        wallet_balance_reader=wallet_balance_reader,
    )
