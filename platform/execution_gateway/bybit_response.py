from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _deep_freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_deep_freeze(v) for v in value)
    if isinstance(value, set):
        return frozenset(_deep_freeze(v) for v in value)
    if isinstance(value, tuple):
        return tuple(_deep_freeze(v) for v in value)
    return value


@dataclass(frozen=True)
class BybitResponse:
    ret_code: int
    ret_msg: str
    result: Any
    ret_ext_info: Any
    time_ms: int

    def __post_init__(self) -> None:
        if isinstance(self.ret_code, bool) or not isinstance(self.ret_code, int):
            raise TypeError(f"ret_code must be int, got: {type(self.ret_code).__name__}")

        if not isinstance(self.ret_msg, str):
            raise TypeError(f"ret_msg must be str, got: {type(self.ret_msg).__name__}")

        if isinstance(self.time_ms, bool) or not isinstance(self.time_ms, int):
            raise TypeError(f"time_ms must be int, got: {type(self.time_ms).__name__}")
        if self.time_ms < 0:
            raise ValueError(f"time_ms must be >= 0, got: {self.time_ms}")

        object.__setattr__(self, "result", _deep_freeze(self.result))
        object.__setattr__(self, "ret_ext_info", _deep_freeze(self.ret_ext_info))
