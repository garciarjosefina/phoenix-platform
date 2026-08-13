from typing import Protocol, runtime_checkable

from execution_gateway.instrument_metadata_contracts import ExecutionInstrumentMetadata


@runtime_checkable
class InstrumentMetadataReader(Protocol):
    def query_instrument_metadata(self, *, symbol: str) -> ExecutionInstrumentMetadata:
        ...
