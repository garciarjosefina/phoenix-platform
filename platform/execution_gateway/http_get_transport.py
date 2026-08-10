from typing import Mapping, Protocol, runtime_checkable


@runtime_checkable
class HttpGetTransport(Protocol):
    def get(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        timeout_seconds: float,
    ) -> str:
        ...
