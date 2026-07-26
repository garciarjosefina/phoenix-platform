from dataclasses import dataclass

_ALLOWED_METHODS = frozenset({"GET", "POST"})


@dataclass(frozen=True)
class BybitEndpoint:
    method: str
    path: str

    def __post_init__(self) -> None:
        if not isinstance(self.method, str):
            raise TypeError(f"method must be str, got: {type(self.method).__name__}")
        if not self.method or self.method.isspace():
            raise ValueError("method must not be empty or whitespace-only")
        if self.method not in _ALLOWED_METHODS:
            raise ValueError(f"method must be GET or POST, got: {self.method!r}")

        if not isinstance(self.path, str):
            raise TypeError(f"path must be str, got: {type(self.path).__name__}")
        if not self.path or self.path.isspace():
            raise ValueError("path must not be empty or whitespace-only")
        if not self.path.startswith("/"):
            raise ValueError(f"path must start with '/', got: {self.path!r}")
        if self.path.startswith("//"):
            raise ValueError(f"path must not start with '//', got: {self.path!r}")
        if "://" in self.path:
            raise ValueError(f"path must not contain a scheme, got: {self.path!r}")
