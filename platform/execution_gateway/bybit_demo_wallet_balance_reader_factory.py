from execution_gateway.bybit_private_get_api import BybitPrivateGetApi
from execution_gateway.bybit_url_builder import BybitUrlBuilder
from execution_gateway.bybit_wallet_balance_reader import BybitWalletBalanceReader
from execution_gateway.bybit_wallet_balance_response_interpreter import (
    BybitWalletBalanceResponseInterpreter,
)

_BYBIT_DEMO_BASE_URL = "https://api-demo.bybit.com"


def create_bybit_demo_wallet_balance_reader(
    *,
    private_get_api: BybitPrivateGetApi,
) -> BybitWalletBalanceReader:
    if not isinstance(private_get_api, BybitPrivateGetApi):
        raise TypeError(
            f"private_get_api must be BybitPrivateGetApi, got: {type(private_get_api).__name__}"
        )
    url_builder = BybitUrlBuilder(base_url=_BYBIT_DEMO_BASE_URL)
    response_interpreter = BybitWalletBalanceResponseInterpreter()
    return BybitWalletBalanceReader(
        private_get_api=private_get_api,
        url_builder=url_builder,
        response_interpreter=response_interpreter,
    )
