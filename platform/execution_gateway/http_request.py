from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True, repr=False)
class HttpRequest:
    url: str
    headers: Mapping[str, str]
    body: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str):
            raise TypeError(f"url must be str, got: {type(self.url).__name__}")
        if not self.url or self.url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        if not isinstance(self.headers, Mapping):
            raise TypeError(f"headers must be a Mapping, got: {type(self.headers).__name__}")
        for k, v in self.headers.items():
            if not isinstance(k, str):
                raise TypeError(f"header key must be str, got: {type(k).__name__}")
            if not isinstance(v, str):
                raise TypeError(f"header value must be str, got: {type(v).__name__}")

        if not isinstance(self.body, str):
            raise TypeError(f"body must be str, got: {type(self.body).__name__}")

        object.__setattr__(self, "headers", MappingProxyType(dict(self.headers)))

    def __repr__(self) -> str:
        header_names = sorted(self.headers.keys())
        return f"HttpRequest(url={self.url!r}, headers={header_names!r}, body=<redacted>)"
