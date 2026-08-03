from dataclasses import dataclass

_VALID_ENVIRONMENTS = {"demo"}


@dataclass(frozen=True)
class GatewayConfig:
    environment: str = "demo"
    dry_run: bool = True
    timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if not isinstance(self.environment, str):
            raise TypeError(f"environment must be str, got: {type(self.environment).__name__}")
        if not self.environment or self.environment.isspace():
            raise ValueError("environment must not be empty or whitespace-only")
        if self.environment not in _VALID_ENVIRONMENTS:
            raise ValueError(
                f"environment must be 'demo', got: {self.environment!r}"
            )

        if not isinstance(self.dry_run, bool):
            raise TypeError(f"dry_run must be bool, got: {type(self.dry_run).__name__}")

        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, int):
            raise TypeError(
                f"timeout_seconds must be int, got: {type(self.timeout_seconds).__name__}"
            )
        if self.timeout_seconds <= 0:
            raise ValueError(
                f"timeout_seconds must be > 0, got: {self.timeout_seconds}"
            )
