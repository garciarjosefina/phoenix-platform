from typing import Protocol, runtime_checkable

from execution_gateway.exchange_state_contracts import ExchangeStateSnapshot


@runtime_checkable
class ExchangeStateReader(Protocol):
    def query_exchange_state(self) -> ExchangeStateSnapshot:
        ...
