from typing import Protocol, runtime_checkable


@runtime_checkable
class MessageSigner(Protocol):
    def sign(self, *, secret: str, message: str) -> str:
        ...
