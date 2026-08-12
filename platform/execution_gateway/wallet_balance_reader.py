from typing import Protocol, runtime_checkable

from execution_gateway.wallet_balance_contracts import WalletBalanceSnapshot


@runtime_checkable
class WalletBalanceReader(Protocol):
    def query_wallet_balance(self) -> WalletBalanceSnapshot:
        ...
