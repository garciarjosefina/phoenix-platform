from dataclasses import dataclass


@dataclass(frozen=True)
class HttpRequest:
    url: str
    headers: dict[str, str]
    body: str

    def __post_init__(self) -> None:
        if not isinstance(self.url, str):
            raise TypeError(f"url must be str, got: {type(self.url).__name__}")
        if not self.url or self.url.isspace():
            raise ValueError("url must not be empty or whitespace-only")

        if not isinstance(self.headers, dict):
            raise TypeError(f"headers must be dict, got: {type(self.headers).__name__}")
        for k, v in self.headers.items():
            if not isinstance(k, str):
                raise TypeError(f"header key must be str, got: {type(k).__name__}")
            if not isinstance(v, str):
                raise TypeError(f"header value must be str, got: {type(v).__name__}")

        if not isinstance(self.body, str):
            raise TypeError(f"body must be str, got: {type(self.body).__name__}")

        object.__setattr__(self, "headers", dict(self.headers))
