from dataclasses import dataclass, field


@dataclass(frozen=True)
class BybitDemoCredentials:
    api_key: str
    api_secret: str = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.api_key, str):
            raise TypeError(f"api_key must be str, got: {type(self.api_key).__name__}")
        if not isinstance(self.api_secret, str):
            raise TypeError(f"api_secret must be str, got: {type(self.api_secret).__name__}")
        if not self.api_key or self.api_key.isspace():
            raise ValueError("api_key must not be empty or whitespace-only")
        if not self.api_secret or self.api_secret.isspace():
            raise ValueError("api_secret must not be empty or whitespace-only")
