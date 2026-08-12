from collections.abc import Mapping

from execution_gateway.bybit_demo_wallet_balance_reader_env_bootstrap import (
    bootstrap_bybit_demo_wallet_balance_reader_from_env,
)
from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


def query_bybit_demo_wallet_balance(
    *,
    environ: Mapping[str, str] | None = None,
) -> WalletBalanceSnapshot:
    reader = bootstrap_bybit_demo_wallet_balance_reader_from_env(environ=environ)
    return reader.query_wallet_balance()
