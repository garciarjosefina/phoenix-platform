from typing import Protocol, runtime_checkable


@runtime_checkable
class JsonSerializer(Protocol):
    def dumps(self, value: object) -> str:
        ...

    def loads(self, value: str) -> object:
        ...
