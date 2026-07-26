from typing import Mapping, Protocol, runtime_checkable


@runtime_checkable
class HttpTransport(Protocol):
    def post(
        self,
        *,
        url: str,
        headers: Mapping[str, str],
        body: str,
        timeout_seconds: float,
    ) -> str:
        ...
