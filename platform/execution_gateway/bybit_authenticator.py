from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class BybitAuthentication:
    timestamp_ms: int
    api_key: str
    recv_window_ms: int
    signature: str = field(repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.timestamp_ms, bool) or not isinstance(self.timestamp_ms, int):
            raise TypeError(f"timestamp_ms must be int, got: {type(self.timestamp_ms).__name__}")
        if self.timestamp_ms < 0:
            raise ValueError(f"timestamp_ms must be >= 0, got: {self.timestamp_ms}")

        if not isinstance(self.api_key, str):
            raise TypeError(f"api_key must be str, got: {type(self.api_key).__name__}")
        if not self.api_key or self.api_key.isspace():
            raise ValueError("api_key must not be empty or whitespace-only")

        if isinstance(self.recv_window_ms, bool) or not isinstance(self.recv_window_ms, int):
            raise TypeError(f"recv_window_ms must be int, got: {type(self.recv_window_ms).__name__}")
        if self.recv_window_ms <= 0:
            raise ValueError(f"recv_window_ms must be > 0, got: {self.recv_window_ms}")

        if not isinstance(self.signature, str):
            raise TypeError(f"signature must be str, got: {type(self.signature).__name__}")
        if not self.signature or self.signature.isspace():
            raise ValueError("signature must not be empty or whitespace-only")


@runtime_checkable
class BybitAuthenticator(Protocol):
    def authenticate(self, *, body: str) -> BybitAuthentication:
        ...
