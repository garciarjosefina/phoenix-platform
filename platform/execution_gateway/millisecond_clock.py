from typing import Protocol, runtime_checkable


@runtime_checkable
class MillisecondClock(Protocol):
    def now_ms(self) -> int:
        ...
